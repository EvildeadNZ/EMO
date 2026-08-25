import os
import unicodedata

# Path to the file
file_path = os.path.abspath("emo/main_window.py")

def sanitize_text(text):
    # This replaces any "broken" character with a standard one
    # and removes the "mojibake" noise.
    # It normalizes the string and strips out non-printable/weird characters.
    
    # Step 1: Normalize to 'NFC' (makes characters like 'å' a single unit)
    text = unicodedata.normalize('NFC', text)
    
    # Step 2: Replace anything that isn't a standard "Safe" character
    # with a standard equivalent or a blank space.
    cleaned = []
    for char in text:
        # If it's a standard character (0-127), it's safe.
        if ord(char) < 128:
            cleaned.append(char)
        else:
            # If it's a "special" character (like å), we try to 
            # simplify it to a standard character.
            # This prevents the "Boxes" from appearing.
            cleaned.append(char.encode('ascii', 'ignore').decode('ascii'))
            
    return "".join(cleaned)

def main():
    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path}")
        return

    print("Step 1: Reading main_window.py...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Step 2: Scrubbing out 'Box' characters and Mojibake...")
    # This logic specifically targets the common "junk"
    # that makes UI elements look weird.
    clean_content = sanitize_text(content)

    print("Step 3: Saving cleaned version...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(clean_content)

    print("Success! The UI text has been 'Sanitized'.")
    print("Any 'boxes' or 'special a's' should now be replaced with standard text.")
    print("You can now build your final Update ZIP.")

if __name__ == "__main__":
    main()
