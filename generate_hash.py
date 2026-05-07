"""
generate_hash.py — Ruang Statistika
Utilitas untuk generate/verify bcrypt password hash.
Jalankan sekali di terminal: python generate_hash.py

Tidak perlu diinclude di deployment — hanya untuk admin.
"""

import bcrypt
import secrets
import sys


def generate_hash(password: str) -> str:
    """Generate bcrypt hash dari password plaintext."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()


def verify_hash(password: str, hashed: str) -> bool:
    """Verifikasi password terhadap hash yang tersimpan."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def generate_cookie_key(length: int = 32) -> str:
    """Generate random key untuk cookie signing."""
    return secrets.token_hex(length // 2)


if __name__ == "__main__":
    print("=" * 60)
    print("  Ruang Statistika — Password Hash Generator")
    print("=" * 60)

    if len(sys.argv) == 2:
        # Mode: python generate_hash.py <password>
        pw = sys.argv[1]
        h = generate_hash(pw)
        print(f"\nPassword : {pw}")
        print(f"Hash     : {h}")
        print(f"\nSalin hash di atas ke users.yaml")

    elif len(sys.argv) == 3 and sys.argv[1] == "verify":
        # Mode: python generate_hash.py verify <password>
        pw = sys.argv[2]
        print(f"\nMasukkan hash yang tersimpan (paste lalu Enter dua kali):")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        hashed = "".join(lines).strip()
        ok = verify_hash(pw, hashed)
        print(f"\n{'✅ COCOK' if ok else '❌ TIDAK COCOK'}")

    else:
        # Mode interaktif
        print("\n[1] Generate hash password baru")
        print("[2] Generate cookie key baru")
        print("[3] Verifikasi password vs hash")
        print()
        choice = input("Pilih (1/2/3): ").strip()

        if choice == "1":
            pw = input("Masukkan password: ").strip()
            if not pw:
                print("Password tidak boleh kosong.")
                sys.exit(1)
            h = generate_hash(pw)
            print(f"\n✅ Hash siap disalin ke users.yaml:")
            print(f'   password: "{h}"')

        elif choice == "2":
            key = generate_cookie_key()
            print(f"\n✅ Cookie key baru:")
            print(f"   key: \"{key}\"")

        elif choice == "3":
            pw = input("Password plaintext: ").strip()
            h = input("Hash tersimpan    : ").strip()
            ok = verify_hash(pw, h)
            print(f"\n{'✅ Password cocok!' if ok else '❌ Password TIDAK cocok.'}")

        else:
            print("Pilihan tidak valid.")
