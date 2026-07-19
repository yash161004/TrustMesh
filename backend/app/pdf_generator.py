from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_session_pdf(session_id: str, session: dict, messages: list, trust_report: dict, ledger: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Negotiation Session Report", styles['Title']))
    story.append(Spacer(1, 12))

    # Metadata
    story.append(Paragraph("Session Metadata", styles['Heading2']))
    story.append(Paragraph(f"<b>Session ID:</b> {session_id}", styles['Normal']))
    story.append(Paragraph(f"<b>Status:</b> {session.get('status', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Created At:</b> {session.get('created_at', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Buyer Agent:</b> {session.get('buyer_agent_id', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Seller Agent:</b> {session.get('seller_agent_id', 'N/A')}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Trust Scores
    story.append(Paragraph("Trust Scores & Violations", styles['Heading2']))
    if trust_report:
        buyer_score = trust_report.get('buyer_score', {})
        seller_score = trust_report.get('seller_score', {})
        story.append(Paragraph(f"<b>Buyer Score:</b> {buyer_score.get('overall_score', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"<b>Seller Score:</b> {seller_score.get('overall_score', 'N/A')}", styles['Normal']))
        
        violations = trust_report.get('violations', [])
        if violations:
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Violations detected:</b>", styles['Normal']))
            for v in violations:
                desc = str(v.get('description', ''))
                for c in "₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹":
                    desc = desc.replace(c, "")
                story.append(Paragraph(f"- {v.get('agent_id')}: {v.get('violation_type')} ({v.get('severity')}) at turn {v.get('message_turn')}. {desc}", styles['Normal']))
        else:
            story.append(Spacer(1, 6))
            story.append(Paragraph("No violations detected.", styles['Normal']))
    else:
        story.append(Paragraph("Trust report not available.", styles['Normal']))
    story.append(Spacer(1, 12))

    # Ledger Verification
    story.append(Paragraph("Ledger Verification", styles['Heading2']))
    if ledger:
        chain_valid = ledger.get('chain_valid', False)
        entry_count = len(ledger.get('entries', []))
        story.append(Paragraph(f"<b>Chain Valid:</b> {chain_valid}", styles['Normal']))
        story.append(Paragraph(f"<b>Entry Count:</b> {entry_count}", styles['Normal']))
    else:
        story.append(Paragraph("Ledger data not available.", styles['Normal']))
    story.append(Spacer(1, 12))

    # Transcript
    story.append(Paragraph("Negotiation Transcript", styles['Heading2']))
    for msg in messages:
        sender = msg.get('sender', 'Unknown')
        turn = msg.get('turn_number', '?')
        msg_type = msg.get('message_type', '')
        price = msg.get('price', 'N/A')
        quantity = msg.get('quantity', 'N/A')
        text = f"<b>Turn {turn} - {sender} ({msg_type})</b><br/>"
        text += f"Price: {price}, Quantity: {quantity}<br/>"
        
        # Unicode sanitization for subscript/superscript only
        notes = str(msg.get('notes', ''))
        if notes:
            for c in "₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹":
                notes = notes.replace(c, "")
            text += f"Notes: {notes}"
        story.append(Paragraph(text, styles['Normal']))
        story.append(Spacer(1, 6))

    doc.build(story)
    return buffer.getvalue()
