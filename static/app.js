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
const result = document.getElementById('result');
const matchInfo = document.getElementById('match-info');
const downloadLink = document.getElementById('download-link');
const error = document.getElementById('error');
const errorText = document.getElementById('error-text');
const retryBtn = document.getElementById('retry-btn');

let selectedFile = null;

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

    showProgress('Converting your resume...');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('job_description', jdInput.value.trim());

    try {
        const response = await fetch('/tailor', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Something went wrong');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        const matchScore = response.headers.get('X-Match-Score');
        const keywords = response.headers.get('X-Keywords-Added');

        showResult(url, matchScore, keywords);
    } catch (err) {
        showError(err.message);
    }
});

retryBtn.addEventListener('click', () => {
    error.classList.add('hidden');
    form.style.display = '';
});

function showProgress(msg) {
    form.style.display = 'none';
    result.classList.add('hidden');
    error.classList.add('hidden');
    progress.classList.remove('hidden');
    progressText.textContent = msg;
}

function showResult(url, score, keywords) {
    progress.classList.add('hidden');
    result.classList.remove('hidden');
    downloadLink.href = url;
    downloadLink.download = 'tailored_resume.pdf';
    if (score) {
        matchInfo.textContent = `ATS Match Score: ${score}%` +
            (keywords ? ` | Keywords added: ${keywords}` : '');
    }
}

function showError(msg) {
    progress.classList.add('hidden');
    form.style.display = 'none';
    error.classList.remove('hidden');
    errorText.textContent = msg;
}
