import requests
import os
import json
import urllib3
import time
from moviepy.editor import concatenate_videoclips, VideoFileClip

TEST = True

SYNTHESIA_API_KEY = '719c0c6ab9573006a956f501fee80e1d'

avatars = {
    'Male Doctor': 'james_costume1_cameraA',
    'Female Doctor': 'mallory_costume1_cameraA',
    'Male Patient': 'vincent_costume2_cameraA',
    'Female Patient': 'bridget_costume2_cameraA'
}

def getTemplates():
  url = "https://api.synthesia.io/v2/templates"
  http = urllib3.PoolManager()
  r = http.request(
      'GET',
      url,
      headers={
          'Authorization': SYNTHESIA_API_KEY
      }
  )
  response = json.loads(r.data)
  templates = response['templates']

  resultMap = {}

  for template in templates:
    title = template['title']
    if title.startswith('DH'):
      template_id = template['id']
      title = title[3:]
      resultMap[title] = template_id
  
  return resultMap


def createAvatarDialogue(character, gender, avatars, line):
  avatarName = gender + ' ' + character
  avatarID = avatars[avatarName]

  if TEST:
    background = 'off_white'
    
    if character == 'Doctor':
        background = 'white_meeting_room'
    else:
        background = 'white_cafe'

    url = "https://api.synthesia.io/v2/videos"
    
    payload = json.dumps({
        'test': TEST,
        'input': [{
            "scriptText": line,
            "avatar": avatarID,
            'background': background
        }]
    })
    
    http = urllib3.PoolManager()
    r = http.request(
        'POST',
        url,
        body=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': SYNTHESIA_API_KEY
        }
    )

    response = json.loads(r.data)
  
  else:
     url = "https://api.synthesia.io/v2/videos/fromTemplate"
     payload = json.dumps({
      'templateId': avatarID,
      'templateData': {
          'script': line
     },
      'test': TEST
     })

     http = urllib3.PoolManager()
     r = http.request(
        'POST',
        url,
        body=payload,
        headers={
          'Content-Type': 'application/json',
          'Authorization': SYNTHESIA_API_KEY
        }
     )
     response = json.loads(r.data)
  
  print(response)
  return response['id']


def getVideo(ID):
    url = "https://api.synthesia.io/v2/videos/" + ID

    http = urllib3.PoolManager()

    while True:
        r = http.request(
            'GET',
            url,
            headers={
                'Authorization': SYNTHESIA_API_KEY
            }
        )

        response = json.loads(r.data)

        # Check if the status is 'complete'
        if response['status'] == 'complete':
            return response['download']

        # Wait for 30 seconds before the next check
        time.sleep(30)


def createVideo(dialogue, docGender, patGender):
   lines = dialogue.split('\n')
   
   if TEST:
      templates = avatars
   else:
      templates = getTemplates()
   
   vidIDs = []
   video_files = []

   # Iterate through script, making clips for each person
   for line in lines:
      if line.startswith("Doctor:"):
        if docGender:
           vid = createAvatarDialogue('Doctor', 'Female', templates, line[8:])
        else:
           vid = createAvatarDialogue('Doctor', 'Male', templates, line[8:])
      elif line.startswith("Patient:"):
        if patGender:
           vid = createAvatarDialogue('Patient', 'Female', templates, line[9:])
        else:
            vid = createAvatarDialogue('Patient', 'Male', templates, line[9:])
      else:
        continue
      vidIDs.append(vid)
   
   for vid in vidIDs:
    downloadURL = getVideo(vid)
    response = requests.get(downloadURL)
    file_name = f"{vid}.mp4"
    open(file_name, "wb").write(response.content)
    video_files.append(file_name)
        
   # Concatenate videos
   print(video_files)
   clips = [VideoFileClip(file) for file in video_files]
   final_clip = concatenate_videoclips(clips)
   final_clip.write_videofile(os.path.join('outputs', "final_video.mp4"), audio_codec='aac')