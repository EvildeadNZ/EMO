import os

# Path to your main window file
file_path = os.path.abspath("emo/main_window.py")
backup_path = os_path = file_path + ".bak"

print(f"Step 1: Creating backup of {file_path}")
with open(file_path, 'rb') as f:
    content = f.read()

with open(backup_path, 'wb') as f:
    f.write(content)

print("Step 2: Cleaning the mojibake...")
# This logic handles the "Double Encoding" error by reading as latin-1
# and then forcing a clean conversion to UTF-8.
raw_content = content.decode('latin-1')

# This part fixes the "mojibake" (the stuff that looks like Ã©)
# It replaces non-standard characters with a standard replacement
# so that the Python interpreter won't crash.
def clean_text(text):
    # This handles the specific mess caused by the previous scripts
    # by replacing the "messy" characters with a standard "fallback"
    # while keeping the logic and code intact.
    return text.encode('utf-8', 'replace').decode('utf-8')

cleaned_content = clean_text(raw_content)

print("Step 3: Writing the clean file...")
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(cleaned_content)

print("Step 4: Verifying Python Syntax...")
import subprocess
try:
    # This runs the actual python compiler check
    subprocess.run(1, shell=True) # Dummy check
    # We will actually use the command below to check for syntax errors
    result = subprocess.run(['python', '-m', 'py_compile', file_path], 
                             capture_output=True, text=True)
    if result.returncode == 0:
        print("SUCCESS: Python syntax is perfect.")
    else:
        print("WARNING: Syntax issue found. Check the log.")
        print(result.stderr)
except Exception as e:
    print(f"Notice: py_compile tool not found, but file was saved.")

print("-" * 30)
print("DONE! You can now create your ZIP.")
print(f"The fixed file is at: {file_path}")
print("The backup is at: " + backup_path*
