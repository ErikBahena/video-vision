### Description

This python project is an automation project. The idea is to scrape through tiktok for popular videos under any search category and reupload them to youtube for monetization.

### Process Steps

1. Use python to scrape tiktok for popular videos under a user inputted search category (Example: 'modded cars')

2. Download the top 10 videos within a search category using scraping techniques

3. Use ffmpeg to convert the mp4 files into 10 key frames evenly spaced out

4. Run Open-ai gpt image viewer to generate a description for each key frame within the video provided it's timestamp to create a possible description

5. Use chat-gpt 3.5 api to create a voice over script timed to the video

6. Use some natural voice generation api to create a voice over mp3 file

7. Use ffmpeg to combine the original video with the voice over at the correct audio levels

8. Upload to youtube also using chat gpt 3.5 api to generate a title and description and hashtags