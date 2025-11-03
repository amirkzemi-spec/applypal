import subprocess

print("🧹 Cleaning up legacy Telegram packages...")
bad_pkgs = ["telegram", "telebot", "python-telegram-bot"]
for pkg in bad_pkgs:
    subprocess.run(["pip", "uninstall", "-y", pkg])

subprocess.run(["pip", "install", "--no-cache-dir", "python-telegram-bot==20.8"])
print("✅ Clean installation complete.")
