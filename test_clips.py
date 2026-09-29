import requests

url = 'http://127.0.0.1:8000/clips?video_name=1_Silent_Hill_Townfall%2FSilentHillTownFall_1.mp4'
try:
    response = requests.get(url)
    print(response.json())
except Exception as e:
    print(e)
