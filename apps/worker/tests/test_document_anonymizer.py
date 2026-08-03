from parsers.anonymizer import PersonalDataAnonymizer, residual_counts
from parsers.artifact import ParseBlock, ParsedDocument, ParserInfo, ParseQuality


def test_anonymizer_scrubs_supported_pii_and_comment_author_metadata():
    parsed = ParsedDocument(
        plain_text=(
            "Иван Петров owns the Gate 2 launch. "
            "Contact ivan.petrov@example.com or +7 999 123-45-67.\n\n"
            "Карта 4111 1111 1111 1111. ИНН 1234567890. "
            "Адрес: г. Москва, ул. Тестовая, д. 1, кв. 2. IP 192.0.2.1. "
            "Ссылка https://example.com/reset?token=abcdef1234567890. "
            "ID USR-123456789012345678901234-END.\n\n"
            "Comment 0 by Anna Smith\nNeeds proof from Петров."
        ),
        markdown=(
            "Иван Петров owns the Gate 2 launch. "
            "Contact ivan.petrov@example.com or +7 999 123-45-67.\n\n"
            "Карта 4111 1111 1111 1111. ИНН 1234567890. "
            "Адрес: г. Москва, ул. Тестовая, д. 1, кв. 2. IP 192.0.2.1. "
            "Ссылка https://example.com/reset?token=abcdef1234567890. "
            "ID USR-123456789012345678901234-END.\n\n"
            "**Comment 0 by Anna Smith**\n\nNeeds proof from Петров."
        ),
        blocks=[
            ParseBlock(
                id="b0001",
                type="paragraph",
                text="Иван Петров owns the Gate 2 launch.",
                markdown="Иван Петров owns the Gate 2 launch.",
                page=None,
                text_span={"start": 0, "end": 34},
                hash="old",
            ),
            ParseBlock(
                id="b0002",
                type="comment",
                text="Comment 0 by Anna Smith\nNeeds proof from Петров.",
                markdown="**Comment 0 by Anna Smith**\n\nNeeds proof from Петров.",
                page=None,
                text_span={"start": 36, "end": 84},
                hash="old",
                metadata={"part": "word/comments.xml", "comment_author": "Anna Smith", "comment_email": "anna.smith@example.org"},
            ),
        ],
        parser=ParserInfo(name="test"),
        quality=ParseQuality(char_count=120, block_count=2),
    )

    anonymized, report = PersonalDataAnonymizer().anonymize_document(parsed)

    assert "Иван" not in anonymized.plain_text
    assert "Петров" not in anonymized.plain_text
    assert "Anna Smith" not in anonymized.markdown
    assert "ivan.petrov@example.com" not in anonymized.plain_text
    assert "+7 999 123-45-67" not in anonymized.plain_text
    assert "4111 1111 1111 1111" not in anonymized.plain_text
    assert "1234567890" not in anonymized.plain_text
    assert "ул. Тестовая" not in anonymized.plain_text
    assert "192.0.2.1" not in anonymized.plain_text
    assert "https://example.com" not in anonymized.plain_text
    assert "USR-123456789012345678901234-END" not in anonymized.plain_text
    assert "[PERSON_001]" in anonymized.plain_text
    assert "[EMAIL_001]" in anonymized.plain_text
    assert "[PHONE_001]" in anonymized.plain_text
    assert "[BANK_DETAILS_001]" in anonymized.plain_text
    assert "[ADDRESS_001]" in anonymized.plain_text
    assert "[IP_001]" in anonymized.plain_text
    assert "[LINK_001]" in anonymized.plain_text
    assert "[IDENTIFIER_001]" in anonymized.plain_text
    assert anonymized.blocks[1].metadata["comment_author"] == "[PERSON_002]"
    assert anonymized.blocks[1].metadata["comment_email"] == "[EMAIL_002]"
    assert "personal_data_anonymized" in anonymized.quality.warnings
    assert anonymized.parser.options["anonymization"]["enabled"] is True
    assert anonymized.parser.options["anonymization"]["strategy"] == "strict_local_pii_rules"
    assert report.person_replacements > 0
    assert report.email_replacements > 0
    assert report.phone_replacements > 0
    assert report.bank_details_replacements >= 2
    assert report.address_replacements > 0
    assert report.ip_replacements > 0
    assert report.link_replacements > 0
    assert report.identifier_replacements > 0
    assert residual_counts(anonymized.plain_text) == {}


def test_anonymizer_preserves_existing_masks_and_masks_latin_labeled_names():
    text = "Почта [EMAIL_001], телефон [PHONE_001]. Prepared by John Smith."
    anonymizer = PersonalDataAnonymizer()
    anonymizer._collect_name_aliases_from_text(text)

    anonymized = anonymizer.anonymize_text(text)

    assert "[EMAIL_001]" in anonymized
    assert "[PHONE_001]" in anonymized
    assert "John Smith" not in anonymized
    assert "[PERSON_001]" in anonymized
    assert residual_counts(anonymized) == {}


def test_anonymizer_does_not_scrub_gate_challenger_terms_as_person_names():
    parsed = ParsedDocument(
        plain_text="Gate Challenger produces Progress Review evidence.",
        markdown="Gate Challenger produces Progress Review evidence.",
        blocks=[],
        parser=ParserInfo(name="test"),
        quality=ParseQuality(char_count=49, block_count=0),
    )

    anonymized, _ = PersonalDataAnonymizer().anonymize_document(parsed)

    assert "Gate Challenger" in anonymized.plain_text
    assert "Progress Review" in anonymized.plain_text
