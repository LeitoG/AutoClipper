with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target1 = '''                        <div style="font-weight:bold; color:#007acc; font-size:18px; display:flex; justify-content:space-between; align-items:center;">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <input type="checkbox" class="merge-checkbox" data-clip-id="" style="width:16px; height:16px; cursor:pointer;" onclick="event.stopPropagation()">
                                <span>Clip  <span style="font-size:12px; color:#aaa;">()</span></span>
                            </div>'''

replacement1 = '''                        <div style="font-weight:bold; color:#007acc; font-size:18px; display:flex; justify-content:space-between; align-items:center;">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <input type="checkbox" class="merge-checkbox" data-clip-id="" style="width:16px; height:16px; cursor:pointer;" onclick="event.stopPropagation()">
                                <span>Clip  <span style="font-size:12px; color:#aaa;">()</span></span>
                            </div>'''

text = text.replace(target1, replacement1)

target2 = '''                            <div style="font-weight:bold; color:#28a745; font-size:16px;">  <span style="font-size:12px; color:#aaa;"></span></div>'''
replacement2 = '''                            <div style="font-weight:bold; color:#28a745; font-size:16px;">Clip  <span style="font-size:12px; color:#aaa;">()</span></div>'''
text = text.replace(target2, replacement2)

target3 = '''                            <div style="font-weight:bold; color:#f44336; font-size:16px;">  <span style="font-size:12px; color:#aaa;"></span></div>'''
replacement3 = '''                            <div style="font-weight:bold; color:#f44336; font-size:16px;">Clip  <span style="font-size:12px; color:#aaa;">()</span></div>'''
text = text.replace(target3, replacement3)

target4 = '''                            <td style="padding: 10px; width: 140px;">
                                <img src="" style="width:120px; aspect-ratio:16/9; object-fit:cover; border-radius:4px; margin-bottom:5px; background:#000;" onerror="this.style.display='none'">
                                <div style="color: #aaa; font-size:10px;"></div>
                                <div style="color: #d09010; font-size: 10px; margin-top: 3px; word-wrap:break-word; max-width:120px;"></div>
                            </td>'''

replacement4 = '''                            <td style="padding: 10px; width: 140px;">
                                <img src="" style="width:120px; aspect-ratio:16/9; object-fit:cover; border-radius:4px; margin-bottom:5px; background:#000;" onerror="this.style.display='none'">
                                <div style="color: #007acc; font-weight:bold; font-size:12px;">Clip </div>
                                <div style="color: #555; font-size:10px;">()</div>
                                <div style="color: #d09010; font-size: 10px; margin-top: 3px; word-wrap:break-word; max-width:120px;"></div>
                            </td>'''

text = text.replace(target4, replacement4)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed clip numbering rendering")
