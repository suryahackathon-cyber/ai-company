import re

with open("main.py", "r") as f:
    content = f.read()

old = '''        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(traceback.format_exc())
        return {"error": str(e)}'''

new = '''        text = response.text.strip()
        # Strip markdown fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Sanitize control characters and retry
            text = re.sub(r'[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]', '', text)
            try:
                return json.loads(text)
            except json.JSONDecodeError as je:
                # Return raw text as single file if JSON fails
                return {
                    "files": [
                        {
                            "filename": "generated_code.txt",
                            "language": "text",
                            "content": text[:5000]
                        }
                    ]
                }
    except Exception as e:
        print(traceback.format_exc())
        return {"error": str(e)}'''

# Replace second occurrence (build endpoint)
count = content.count(old)
print(f"Found {count} matches")
content = content.replace(old, new, 1)
content = content.replace(old, new, 1)

with open("main.py", "w") as f:
    f.write(content)

import re as re2
print("Done!")
