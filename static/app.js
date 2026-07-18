// static/app.js
const form = document.getElementById('tailor-form');
const fileInput = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');
const browseBtn = document.getElementById('browse-btn');
const fileName = document.getElementById('file-name');
const jdInput = document.getElementById('jd-input');
const submitBtn = document.getElementById('submit-btn');
const progress = document.getElementById('progress');
const progressText = document.getElementById('progress-text');
const verification = document.getElementById('verification');
const error = document.getElementById('error');
const errorText = document.getElementById('error-text');
const retryBtn = document.getElementById('retry-btn');

let selectedFile = null;
let currentData = null;

browseBtn.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) selectFile(e.target.files[0]);
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
        selectFile(file);
    }
});

function selectFile(file) {
    if (file.size > 5 * 1024 * 1024) {
        showError('File too large. Maximum size is 5MB.');
        return;
    }
    if (file.type !== 'application/pdf') {
        showError('Only PDF files are accepted.');
        return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    validateForm();
}

jdInput.addEventListener('input', validateForm);

function validateForm() {
    submitBtn.disabled = !(selectedFile && jdInput.value.trim().length >= 50);
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!selectedFile || jdInput.value.trim().length < 50) return;

    showProgress('Tailoring your resume — this takes 30-60 seconds...');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('job_description', jdInput.value.trim());

    const photoInput = document.getElementById('photo-input');
    if (photoInput.files[0]) {
        formData.append('photo', photoInput.files[0]);
    }

    try {
        const response = await fetch('/tailor', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const text = await response.text();
            let message = 'Something went wrong';
            try {
                const data = JSON.parse(text);
                message = data.detail || message;
            } catch {
                message = text || message;
            }
            throw new Error(message);
        }

        const data = await response.json();
        currentData = data;
        showVerification(data);
    } catch (err) {
        showError(err.message);
    }
});

retryBtn.addEventListener('click', resetUI);
document.getElementById('start-over-btn').addEventListener('click', resetUI);

function resetUI() {
    error.classList.add('hidden');
    verification.classList.add('hidden');
    progress.classList.add('hidden');
    form.style.display = '';
    currentData = null;
}

function showProgress(msg) {
    form.style.display = 'none';
    verification.classList.add('hidden');
    error.classList.add('hidden');
    progress.classList.remove('hidden');
    progressText.textContent = msg;
}

function showVerification(data) {
    progress.classList.add('hidden');
    verification.classList.remove('hidden');

    const realScoreEl = document.getElementById('real-score');
    realScoreEl.textContent = data.match_score + '%';
    document.getElementById('score-detail').textContent =
        data.keywords_found.length + ' of ' + data.keywords_total + ' JD keywords found';
    document.getElementById('claude-score').textContent = data.claude_score + '%';

    if (data.match_score >= 75) realScoreEl.style.color = '#16a34a';
    else if (data.match_score >= 50) realScoreEl.style.color = '#ca8a04';
    else realScoreEl.style.color = '#dc2626';

    renderKeywordTags('keywords-found', data.keywords_found);
    renderKeywordTags('keywords-missing', data.keywords_missing);

    populateEditPanel(data.resume_data);

    const downloadBtn = document.getElementById('download-btn');
    downloadBtn.href = '/download/' + data.request_id;
    downloadBtn.download = 'tailored_resume.pdf';
}

function renderKeywordTags(containerId, keywords) {
    const container = document.getElementById(containerId);
    container.textContent = '';
    if (!keywords.length) {
        const span = document.createElement('span');
        span.style.color = '#888';
        span.style.fontSize = '0.85rem';
        span.textContent = containerId.includes('found') ? 'None detected' : 'All keywords covered!';
        container.appendChild(span);
        return;
    }
    keywords.forEach(kw => {
        const tag = document.createElement('span');
        tag.className = 'keyword-tag';
        tag.textContent = kw;
        container.appendChild(tag);
    });
}

// --- Edit Panel ---

function populateEditPanel(resumeData) {
    document.getElementById('edit-name').value = resumeData.name || '';
    document.getElementById('edit-title').value = resumeData.title || '';
    document.getElementById('edit-linkedin').value = (resumeData.contact && resumeData.contact.linkedin) || '';
    document.getElementById('edit-medium').value = (resumeData.contact && resumeData.contact.medium) || '';
    document.getElementById('edit-summary').value = resumeData.summary || '';

    renderEditableTags('edit-skills', resumeData.skills || [], 'add-skill-input');
    renderEditableTags('edit-certs', resumeData.certifications || [], 'add-cert-input');
    renderExperienceEditor(resumeData.experience || []);
}

function renderEditableTags(containerId, items, inputId) {
    const container = document.getElementById(containerId);
    container.textContent = '';

    items.forEach(item => {
        const tag = document.createElement('span');
        tag.className = 'editable-tag';
        tag.textContent = item;
        tag.title = 'Click to remove';
        tag.addEventListener('click', () => {
            tag.remove();
        });
        container.appendChild(tag);
    });

    const input = document.getElementById(inputId);
    input.value = '';
    input.onkeydown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const val = input.value.trim();
            if (!val) return;
            const tag = document.createElement('span');
            tag.className = 'editable-tag';
            tag.textContent = val;
            tag.title = 'Click to remove';
            tag.addEventListener('click', () => tag.remove());
            container.appendChild(tag);
            input.value = '';
        }
    };
}

function renderExperienceEditor(jobs) {
    const container = document.getElementById('edit-experience');
    container.textContent = '';

    jobs.forEach((job, jobIdx) => {
        const jobDiv = document.createElement('div');
        jobDiv.className = 'edit-job';

        const header = document.createElement('div');
        header.className = 'edit-job-header';
        header.textContent = job.company + ' — ' + job.title + ' (' + job.start_date + ' – ' + job.end_date + ')';
        jobDiv.appendChild(header);

        const bulletList = document.createElement('div');
        bulletList.className = 'edit-bullets';
        bulletList.dataset.jobIdx = jobIdx;

        (job.bullets || []).forEach((bullet, bulletIdx) => {
            bulletList.appendChild(createBulletRow(bullet));
        });

        jobDiv.appendChild(bulletList);

        const addRow = document.createElement('div');
        addRow.className = 'add-bullet-row';
        const addInput = document.createElement('input');
        addInput.type = 'text';
        addInput.placeholder = 'Add bullet point...';
        addInput.className = 'bullet-input';
        addInput.onkeydown = (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const val = addInput.value.trim();
                if (!val) return;
                bulletList.appendChild(createBulletRow(val));
                addInput.value = '';
            }
        };
        addRow.appendChild(addInput);
        jobDiv.appendChild(addRow);

        container.appendChild(jobDiv);
    });
}

function createBulletRow(text) {
    const row = document.createElement('div');
    row.className = 'bullet-row';

    const input = document.createElement('input');
    input.type = 'text';
    input.value = text;
    input.className = 'bullet-input';
    row.appendChild(input);

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'bullet-remove';
    removeBtn.textContent = '×';
    removeBtn.onclick = () => row.remove();
    row.appendChild(removeBtn);

    return row;
}

function collectEditedData() {
    const rd = JSON.parse(JSON.stringify(currentData.resume_data));

    rd.name = document.getElementById('edit-name').value.trim();
    rd.title = document.getElementById('edit-title').value.trim();
    if (!rd.contact) rd.contact = {};
    rd.contact.linkedin = document.getElementById('edit-linkedin').value.trim();
    rd.contact.medium = document.getElementById('edit-medium').value.trim() || undefined;
    rd.summary = document.getElementById('edit-summary').value.trim();

    rd.skills = Array.from(document.querySelectorAll('#edit-skills .editable-tag'))
        .map(el => el.textContent);

    rd.certifications = Array.from(document.querySelectorAll('#edit-certs .editable-tag'))
        .map(el => el.textContent);

    const jobContainers = document.querySelectorAll('#edit-experience .edit-job');
    jobContainers.forEach((jobDiv, idx) => {
        if (rd.experience[idx]) {
            const bullets = Array.from(jobDiv.querySelectorAll('.bullet-row .bullet-input'))
                .map(input => input.value.trim())
                .filter(v => v.length > 0);
            rd.experience[idx].bullets = bullets;
        }
    });

    return rd;
}

// Regenerate button
document.getElementById('regenerate-btn').addEventListener('click', async () => {
    if (!currentData) return;

    const editedData = collectEditedData();
    const btn = document.getElementById('regenerate-btn');
    const downloadBtn = document.getElementById('download-btn');
    btn.disabled = true;
    btn.textContent = 'Regenerating...';

    try {
        const resp = await fetch('/regenerate/' + currentData.request_id, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(editedData),
        });

        if (!resp.ok) {
            const d = await resp.json();
            throw new Error(d.detail || 'Regeneration failed');
        }

        currentData.resume_data = editedData;
        btn.textContent = 'PDF Updated!';
        btn.style.background = '#16a34a';
        downloadBtn.href = '/download/' + currentData.request_id;
        downloadBtn.style.display = 'inline-block';
        setTimeout(() => {
            btn.textContent = 'Regenerate PDF';
            btn.style.background = '';
            btn.disabled = false;
        }, 2000);
    } catch (err) {
        btn.textContent = 'Regenerate PDF';
        btn.disabled = false;
        alert('Error: ' + err.message);
    }
});

function showError(msg) {
    progress.classList.add('hidden');
    form.style.display = 'none';
    error.classList.remove('hidden');
    errorText.textContent = msg;
}
