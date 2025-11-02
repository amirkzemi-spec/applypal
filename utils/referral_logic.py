def check_referral_need(user_input):
    """
    Detects when to refer the user to Nika Visa specialists based on their question content.
    Shows referral earlier (after 1–2 visa-related questions).
    """
    keywords = [
        "visa", "immigration", "embassy", "residence", "permit",
        "migration", "apply for visa", "student visa", "اقامت", "ویزا", "پناه"
    ]
    text = user_input.lower()

    # Count how many visa-like terms appear
    count = sum(1 for k in keywords if k in text)

    if count > 0:
        return (
            "\n\n🤝 It seems you’re asking about visa or residency matters.\n"
            "For official and personalized help, please contact our trusted partner *Nika Visa*:\n"
            "📞 ‎+98 991 077 7743 📲 [t.me/nikavisa_admin](https://t.me/nikavisa_admin)"
        )

    return ""
