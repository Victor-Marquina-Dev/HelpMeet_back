import secrets
import string


def generate_license_key() -> str:
    alphabet = string.ascii_uppercase + string.digits

    def segment(n=4):
        return "".join(secrets.choice(alphabet) for _ in range(n))

    return f"HM-{segment()}-{segment()}-{segment()}-{segment()}"
