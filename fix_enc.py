import sys

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    replacements = {
        'Ã¡': 'á',
        'Ã©': 'é',
        'Ã­': 'í',  # í (i with acute)
        'Ã³': 'ó',
        'Ãº': 'ú',
        'Ã±': 'ñ',
        'Ã‘': 'Ñ',
        'Ã¼': 'ü',
        'Â¡': '¡',
        'Â¿': '¿',
        'Ã ': 'à',
        'Ã¨': 'è',
        'Ã¬': 'ì',
        'Ã²': 'ò',
        'Ã¹': 'ù',
        'Ã\xad': 'í',
        'ðŸŽ¨': '🎨',
        'âœ¨': '✨',
        'ðŸ“·': '📷',
        'ðŸ”„': '🔄',
        'ðŸ“ ': '📝',
        'ðŸŽ¶': '🎵',
        'ðŸ“½': '📽',
        'ðŸŽ¬': '🎬',
        'âŒ¨ï¸ ': '⌨️',
        'ðŸ–±': '🖱',
        'ðŸ”Š': '🔊',
        'ðŸ‘€': '👀',
        'ðŸ§ ': '🧠',
        'ðŸ”¥': '🔥',
        'ðŸ“ˆ': '📈',
        'ðŸ’¥': '💥',
        'ðŸ¤£': '🤣',
        'ðŸ˜‚': '😂',
        'ðŸŽ®': '🎮',
        'ðŸ“²': '📲',
        'âš ï¸ ': '⚠️',
        'ðŸ“': '📱', # close enough
        'ðŸŽ': '🎬',
        'ðŸ”': '🔍'
    }
    
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    # Extra fix for í which is often Ã followed by a weird char
    content = content.replace('Ã\xad', 'í')
    content = content.replace('Ã\xa1', 'á')
    content = content.replace('Ã\xa9', 'é')
    content = content.replace('Ã\xb3', 'ó')
    content = content.replace('Ã\xba', 'ú')
    content = content.replace('Ã\xb1', 'ñ')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed", filepath)

fix_file(r'c:\Users\leone\Desktop\OBS Grabaciones\Exports\Complete Games\templates\index.html')
