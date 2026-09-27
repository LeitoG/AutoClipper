import re

def check_brackets(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    script_start = html.find("<script>") + len("<script>")
    script_end = html.rfind("</script>")
    js_code = html[script_start:script_end]
    
    # Let's write a simple state machine to strip strings, comments, and regex
    stripped = []
    i = 0
    while i < len(js_code):
        if js_code[i:i+2] == '//':
            while i < len(js_code) and js_code[i] != '\\n': i += 1
            continue
        if js_code[i:i+2] == '/*':
            while i < len(js_code) and js_code[i:i+2] != '*/': i += 1
            i += 2
            continue
        if js_code[i] in ('"', "'"):
            quote = js_code[i]
            i += 1
            while i < len(js_code):
                if js_code[i] == '\\\\': i += 2
                elif js_code[i] == quote: i += 1; break
                else: i += 1
            continue
        if js_code[i] == '`':
            i += 1
            while i < len(js_code):
                if js_code[i] == '\\\\': i += 2
                elif js_code[i:i+2] == '${':  # template expression start
                    stripped.append('{')
                    i += 2
                elif js_code[i] == '`': i += 1; break
                else: i += 1
            continue
        stripped.append(js_code[i])
        i += 1
    js_code = "".join(stripped)
    
    stack = []
    line_num = 1
    for char in js_code:
        if char == '\\n':
            line_num += 1
        elif char in "{[(":
            stack.append((char, line_num))
        elif char in "}])":
            if not stack:
                print(f"Error: Unmatched closing bracket '{char}' at line {line_num}")
                return
            last_open, _ = stack.pop()
            pairs = {'{': '}', '[': ']', '(': ')'}
            if pairs[last_open] != char:
                # Let's print the context
                lines = js_code.split('\\n')
                with open("out.txt", "w", encoding="utf-8") as f:
                    f.write("\\n".join(lines[max(0, line_num-5):line_num+5]))
                return
                
    if stack:
        print(f"Error: Unclosed brackets remaining: {stack}")
    else:
        print("Brackets are perfectly balanced!")

check_brackets(r"C:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html")
