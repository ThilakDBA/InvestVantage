import logging

from app.core.logging import configure_logging


def test_provider_transport_logs_do_not_emit_request_urls(capsys) -> None:
    configure_logging("INFO")

    logging.getLogger("httpx").info(
        "HTTP Request: GET https://provider.example/data?token=secret-value"
    )
    logging.getLogger("app.ingestion").info("Ingestion completed")

    captured = capsys.readouterr()
    assert "secret-value" not in captured.err
    assert "Ingestion completed" in captured.err
