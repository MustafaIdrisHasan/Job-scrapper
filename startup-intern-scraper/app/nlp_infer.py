"""Lightweight keyword-based tech stack inference."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Set

from .models import InternshipListing

LANGS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "go",
    "rust",
    "ruby",
    "c++",
    "c#",
    "swift",
    "kotlin",
}
WEB = {"react", "vue", "angular", "node", "django", "flask", "fastapi", "graphql"}
CLOUD = {"aws", "azure", "gcp", "docker", "kubernetes", "terraform"}
DATA = {"sql", "postgres", "mysql", "mongodb", "spark", "pandas", "numpy"}
MOBILE = {"android", "ios", "react native", "flutter"}
ML = {"machine learning", "deep learning", "pytorch", "tensorflow", "mlops"}
DEVOPS = {"ci/cd", "github actions", "jenkins", "devops"}
SECURITY = {"security", "penetration testing", "iam", "oauth"}
PRODUCT = {"figma", "jira", "notion"}

CATEGORY_DEFAULTS = {
    "backend": ["Python", "REST APIs", "Postgres", "Docker"],
    "frontend": ["TypeScript", "React", "CSS", "Design Systems"],
    "fullstack": ["JavaScript", "React", "Node.js", "SQL"],
    "data": ["Python", "Pandas", "SQL", "Data Visualization"],
    "ml": ["Python", "TensorFlow", "Model Evaluation"],
    "mobile": ["Kotlin", "Android Studio", "REST APIs"],
    "security": ["Python", "Security Auditing", "IAM"],
    "product": ["Figma", "User Research", "A/B Testing"],
}

ROLE_KEYWORDS = {
    "backend": {"backend", "back-end", "server", "api"},
    "frontend": {"frontend", "front-end", "ui", "web"},
    "fullstack": {"fullstack", "full-stack"},
    "data": {"data", "analytics", "bi"},
    "ml": {"ml", "machine learning", "ai"},
    "mobile": {"mobile", "android", "ios"},
    "security": {"security", "infosec"},
    "product": {"product", "ux", "designer"},
}


def infer_for_listing(listing: InternshipListing) -> List[str]:
    """Infer a recommended tech stack for the provided listing."""

    text = " ".join(
        filter(
            None,
            [
                listing.role_title,
                listing.responsibilities,
                listing.pay or "",
                listing.location or "",
            ],
        )
    ).lower()

    matched = _collect_keywords(text)
    if matched:
        return _format_suggestions(matched)

    role_category = _fallback_category(listing.role_title.lower())
    defaults = CATEGORY_DEFAULTS.get(role_category, ["Python", "REST APIs", "SQL"])

    return defaults[:4]


def _collect_keywords(text: str) -> Set[str]:
    keywords: Set[str] = set()

    def match_set(candidates: Iterable[str], label: str) -> None:
        for candidate in candidates:
            pattern = r"\b" + re.escape(candidate) + r"\b"
            if re.search(pattern, text):
                keywords.add(candidate)

    match_set(LANGS, "lang")
    match_set(WEB, "web")
    match_set(CLOUD, "cloud")
    match_set(DATA, "data")
    match_set(MOBILE, "mobile")
    match_set(ML, "ml")
    match_set(DEVOPS, "devops")
    match_set(SECURITY, "security")
    match_set(PRODUCT, "product")

    return keywords


def _format_suggestions(keywords: Set[str]) -> List[str]:
    normalized = []
    for keyword in keywords:
        if keyword == "ci/cd":
            normalized.append("CI/CD")
        elif keyword == "aws":
            normalized.append("AWS")
        elif keyword == "gcp":
            normalized.append("Google Cloud")
        else:
            normalized.append(keyword.title())
    normalized.sort()
    return normalized[:7]


def _fallback_category(role_title: str) -> str:
    for category, tokens in ROLE_KEYWORDS.items():
        if any(token in role_title for token in tokens):
            return category
    return "fullstack"

