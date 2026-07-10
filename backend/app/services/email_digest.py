from __future__ import annotations

import smtplib
from datetime import date
from email.message import EmailMessage
from html import escape

from ..config import get_settings
from ..models import ScanResult
from ..universe import sp500_holding_lookup


class EmailDigestService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.email_smtp_host
            and self.settings.email_smtp_username
            and self.settings.email_smtp_password
            and self.settings.email_digest_recipient
        )

    def send(self, results: list[ScanResult]) -> None:
        if not self.configured:
            raise RuntimeError(
                "邮件未配置：请设置 EMAIL_SMTP_USERNAME 与 EMAIL_SMTP_PASSWORD（Gmail 应用专用密码）"
            )
        message = self._build_message(results)
        with smtplib.SMTP(
            self.settings.email_smtp_host,
            self.settings.email_smtp_port,
            timeout=30,
        ) as smtp:
            if self.settings.email_smtp_starttls:
                smtp.starttls()
            smtp.login(
                self.settings.email_smtp_username,
                self.settings.email_smtp_password,
            )
            smtp.send_message(message)

    def _build_message(self, results: list[ScanResult]) -> EmailMessage:
        message = EmailMessage()
        sender = self.settings.email_smtp_from or self.settings.email_smtp_username
        message["From"] = sender
        message["To"] = self.settings.email_digest_recipient
        message["Subject"] = f"[PA Selector] {date.today().isoformat()} 前20候选"
        text_rows = [
            "排名 | Ticker | Score | 市值排名 | 规则 | Entry | Stop | Target | R/R",
            "-" * 88,
        ]
        html_rows: list[str] = []
        lookup = sp500_holding_lookup()
        for index, result in enumerate(results, 1):
            holding = lookup.get(result.symbol)
            cap_rank = holding["rank"] if holding else "—"
            text_rows.append(
                f"{index:>2} | {result.symbol:<6} | {result.score:>5.1f} | "
                f"{str(cap_rank):>4} | {result.rule_name} | {result.entry:.2f} | "
                f"{result.stop:.2f} | {result.target:.2f} | {result.risk_reward:.2f}R"
            )
            html_rows.append(
                "<tr>"
                f"<td>{index}</td><td><strong>{escape(result.symbol)}</strong></td>"
                f"<td>{result.score:.1f}</td><td>{cap_rank}</td>"
                f"<td>{escape(result.rule_name)}</td><td>{result.entry:.2f}</td>"
                f"<td>{result.stop:.2f}</td><td>{result.target:.2f}</td>"
                f"<td>{result.risk_reward:.2f}R</td>"
                "</tr>"
            )
        message.set_content(
            "每日价格行为候选（只读研究，不构成投资建议）\n\n" + "\n".join(text_rows)
        )
        message.add_alternative(
            """
            <html><body style="font-family:Arial,sans-serif;color:#172235">
            <h2>价格行为候选前20</h2>
            <p>只读研究，不构成投资建议。排序：Score 降序，同分按市值由大到小。</p>
            <table cellpadding="7" cellspacing="0" border="1" style="border-collapse:collapse;font-size:13px">
            <thead><tr><th>#</th><th>Ticker</th><th>Score</th><th>市值排名</th><th>规则</th><th>Entry</th><th>Stop</th><th>Target</th><th>R/R</th></tr></thead>
            <tbody>
            """
            + "".join(html_rows)
            + "</tbody></table></body></html>",
            subtype="html",
        )
        return message


email_digest_service = EmailDigestService()
