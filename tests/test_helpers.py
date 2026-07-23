import pytest

from main import normalize_for_matching, keyword_in_text, dedupe_keywords, compute_match_score


class TestNormalizeForMatching:
    def test_hyphens_become_spaces(self):
        assert normalize_for_matching("CI-CD") == "ci cd"

    def test_underscores_become_spaces(self):
        assert normalize_for_matching("site_reliability") == "site reliability"

    def test_slashes_become_spaces(self):
        assert normalize_for_matching("CI/CD") == "ci cd"

    def test_lowercased(self):
        assert normalize_for_matching("Kubernetes") == "kubernetes"

    def test_stripped(self):
        assert normalize_for_matching("  Docker  ") == "docker"

    def test_combined(self):
        assert normalize_for_matching(" CI/CD-Pipeline_v2 ") == "ci cd pipeline v2"

    def test_empty_string(self):
        assert normalize_for_matching("") == ""

    def test_no_special_chars(self):
        assert normalize_for_matching("terraform") == "terraform"


class TestKeywordInText:
    def test_exact_match(self):
        text = normalize_for_matching("Experience with AWS and Kubernetes")
        assert keyword_in_text("AWS", text) is True

    def test_hyphenated_vs_spaced(self):
        text = normalize_for_matching("Built CI/CD pipelines")
        assert keyword_in_text("CI-CD", text) is True

    def test_slash_variant_matches(self):
        text = normalize_for_matching("Built CI-CD pipelines")
        assert keyword_in_text("CI/CD", text) is True

    def test_no_space_match(self):
        text = normalize_for_matching("Experienced devops engineer")
        assert keyword_in_text("DevOps", text) is True

    def test_compound_no_space(self):
        text = normalize_for_matching("Built infrastructure with terraform")
        assert keyword_in_text("Terraform", text) is True

    def test_false_when_absent(self):
        text = normalize_for_matching("Experience with AWS and Docker")
        assert keyword_in_text("Kubernetes", text) is False

    def test_false_partial_no_match(self):
        text = normalize_for_matching("Experience with Java")
        assert keyword_in_text("JavaScript", text) is False

    def test_multi_word_keyword(self):
        text = normalize_for_matching("Site reliability engineering experience")
        assert keyword_in_text("site-reliability", text) is True


class TestDedupeKeywords:
    def test_removes_normalized_duplicates(self):
        keywords = ["CI/CD", "ci-cd", "CI_CD"]
        result = dedupe_keywords(keywords)
        assert result == ["CI/CD"]

    def test_keeps_first_occurrence(self):
        keywords = ["ci-cd", "CI/CD"]
        result = dedupe_keywords(keywords)
        assert result == ["ci-cd"]

    def test_preserves_order(self):
        keywords = ["AWS", "Kubernetes", "Docker", "aws"]
        result = dedupe_keywords(keywords)
        assert result == ["AWS", "Kubernetes", "Docker"]

    def test_no_duplicates(self):
        keywords = ["AWS", "Kubernetes", "Docker"]
        result = dedupe_keywords(keywords)
        assert result == ["AWS", "Kubernetes", "Docker"]

    def test_empty_list(self):
        assert dedupe_keywords([]) == []

    def test_single_item(self):
        assert dedupe_keywords(["AWS"]) == ["AWS"]


class TestComputeMatchScore:
    def test_all_found(self):
        resume = "Experienced in AWS, Kubernetes, and Docker"
        keywords = ["AWS", "Kubernetes", "Docker"]
        result = compute_match_score(resume, keywords)
        assert result["score"] == 100
        assert len(result["found"]) == 3
        assert len(result["missing"]) == 0
        assert result["total"] == 3

    def test_none_found(self):
        resume = "Experienced in Java and Spring Boot"
        keywords = ["AWS", "Kubernetes", "Docker"]
        result = compute_match_score(resume, keywords)
        assert result["score"] == 0
        assert len(result["found"]) == 0
        assert len(result["missing"]) == 3

    def test_partial_match(self):
        resume = "Built CI/CD pipelines using AWS"
        keywords = ["AWS", "CI/CD", "Terraform", "Ansible"]
        result = compute_match_score(resume, keywords)
        assert result["score"] == 50
        assert len(result["found"]) == 2
        assert len(result["missing"]) == 2

    def test_empty_keyword_list_returns_zero(self):
        resume = "Experienced in AWS and Kubernetes"
        keywords = []
        result = compute_match_score(resume, keywords)
        assert result["score"] == 0
        assert result["total"] == 0
        assert result["found"] == []
        assert result["missing"] == []

    def test_deduplicates_before_scoring(self):
        resume = "Built CI/CD pipelines"
        keywords = ["CI/CD", "ci-cd", "CI_CD"]
        result = compute_match_score(resume, keywords)
        assert result["total"] == 1
        assert result["score"] == 100
