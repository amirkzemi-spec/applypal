import subprocess, sys, importlib.util

print("🧹 Checking for shadow Telegram packages...")

# uninstall everything that can conflict
for pkg in ["telegram", "telebot", "python-telegram-bot"]:
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", pkg])

# reinstall only the right one
subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "python-telegram-bot==20.8"])

# show which module will actually load
spec = importlib.util.find_spec("telegram")
print("✅ Telegram module path:", spec.origin if spec else "NOT FOUND")
import subprocess, sys, importlib.util

print("🧹 Checking for shadow Telegram packages...")

# uninstall any legacy Telegram packages
for pkg in ["telegram", "telebot", "python-telegram-bot"]:
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", pkg])

# reinstall the correct one
subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "python-telegram-bot==20.8"])

# show which package is loaded
spec = importlib.util.find_spec("telegram")
print("✅ Telegram module path:", spec.origin if spec else "NOT FOUND")
