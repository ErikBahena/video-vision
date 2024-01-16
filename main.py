import json
import os
import subprocess
import base64
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

config = {
    "gpt_vision_outputs_folder": "/Users/erikbahena/Desktop/tt-yt-auto-uploader/gpt-vision-outputs",
    "captions_folder": "/Users/erikbahena/Desktop/tt-yt-auto-uploader/captions",
    "keyframes_folder": "/Users/erikbahena/Desktop/tt-yt-auto-uploader/keyframes",
    "json_file_path": "/Users/erikbahena/Desktop/tt-yt-auto-uploader/top_videos.json",
}

processed_videos = []

def get_data():
    with open(config["json_file_path"]) as f:
        data = json.load(f)
        return data
    
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def format_timestamp(seconds: float, always_include_hours: bool = False, decimal_marker: str = "."):
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000

    hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""

    return (f"{hours_marker}{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}")
    
def get_video_duration(file_path):
    """Gets the duration of the video in seconds.ms using ffprobe."""
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        duration = result.stdout.decode("utf-8")

        if duration:
            # return as float rounded to 2 decimal places
            return round(float(duration), 2)
        else:
            raise Exception ("Corrupted file.", file_path)
    except Exception as e:
        print(f"Error during duration retrieval: {e}")
        return False
    
# 3. Uses ffmpeg to convert the mp4 files into 10 key frames evenly spaced out based on the duration of the video.
def create_keyframes(file_path, duration):
    """Creates 10 keyframes evenly spaced out based on the duration of the video."""
    try:
        frame_data = []
        # get the duration of the video in seconds
        duration = int(duration)

        # create a list of 10 evenly spaced out timestamps
        timestamps = [round(i * duration / 9) for i in range(10)]

        print("Duration:", duration, "|" "Key Frame Times:", timestamps)

        # create a list of commands to be run by ffmpeg. Run silently.
        cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'panic', '-i', file_path]

        for timestamp in timestamps:
            cmd.append('-ss')
            cmd.append(str(timestamp))
            cmd.append('-vframes')
            cmd.append('1')
            keyframes_sub_dir = f"{config['keyframes_folder']}/{os.path.basename(file_path).split('.')[0]}"

            # create a subdirectory for each video if it doesn't exist
            if not os.path.exists(keyframes_sub_dir):
                os.mkdir(keyframes_sub_dir)

            output_file_name = f"{keyframes_sub_dir}/{timestamp}.jpg"
            cmd.append(output_file_name)

            # add the output file name to the frame_data list
            frame_data.append({
                "timestamp": timestamp,
                "file_name": output_file_name
            })
        # run the command
        subprocess.run(cmd)

        return frame_data
    except Exception as e:
        print(f"Error during keyframe creation: {e}")
        return False
    
# def next_formatted_timestamp(keyframes, current_key_frame_index, total_video_duration):
#     """Gets the next timestamp from the list of keyframes."""
#     try:
#         # if the index is not the last item in the list, return the next item
#         if current_key_frame_index < len(keyframes) - 1:
#             return format_timestamp(keyframes[current_key_frame_index + 1]["timestamp"], True)
#         else:
#             # if the index is the last item in the list, return the total video duration
#             return format_timestamp(total_video_duration, True)
#     except Exception as e:
#         print(f"Error during next timestamp retrieval: {e}")
#         return False
    
def get_api_response(prompt, images):
    content = []
    content.append(prompt)

    for image in images:
        content.append(image)

    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": content
            }
        ],
        max_tokens=4096,
    )

    return response

def describe_keyframes(video):
    """Describes the keyframes of the video using the open ai gpt 4 vision."""
    try:
        keyframes = video["KEYFRAMES"]
        total_video_duration = video["VIDEO_DURATION"]
        prompt_text: str = f"You are given a series of evenly spaced out keyframes from a video. The video duration is {format_timestamp(total_video_duration, True)} long. Be non callant and almost rude but funny. Return a vtt voice over these images. Note the timestamps. "

        images = []
        total_words = 0  # Initialize total word count

        for index, keyframe in enumerate(keyframes):
            keyframe_image = keyframe["file_name"]
            formatted_timestamp = format_timestamp(keyframe["timestamp"], True)
            is_first_timestamp = index == 0
            is_last_timestamp = index == len(keyframes) - 1
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encode_image(keyframe_image)}",
                }
            })

            # Estimate word count for each segment
            segment_duration = keyframes[index + 1]["timestamp"] - keyframe["timestamp"] if not is_last_timestamp else total_video_duration - keyframe["timestamp"]
            segment_word_limit = segment_duration * 150 / 60  # Words for each segment

            # if first frame description:
            if is_first_timestamp:
                prompt_text += f" Image {index + 1}/{len(keyframes)} is taken at {formatted_timestamp}. Start with a good hook to engage the viewer (max {segment_word_limit} words)."
            elif is_last_timestamp:
                prompt_text += f" Image {index + 1}/{len(keyframes)} is taken at {formatted_timestamp}. End with a call to action (max {segment_word_limit} words)."
            else:
                prompt_text += f" Image {index + 1}/{len(keyframes)} is taken at {formatted_timestamp} (max {segment_word_limit} words)."

            total_words += segment_word_limit

            if total_words > (total_video_duration * 150 / 60):
                print("Warning: Total words exceed video duration capacity. Consider reducing content.")

        return get_api_response({ "type": "text", "text": prompt_text }, images)
    except Exception as e:
        print(f"Error during keyframe description: {e}")
        return False

if __name__ == "__main__":
    processed_videos = get_data()
    # log out how many videos we have
    print(f"Processing {len(processed_videos)} videos:")

    try: 
        # update the VIDEO_DURATION field in the json file where the VIDEO_PATH is the same as the file_path
        for video in processed_videos:
            file_path = video["VIDEO_PATH"]
            duration = get_video_duration(file_path)

            if duration:
                video["VIDEO_DURATION"] = duration
            else:
                # remove the video from the list if it's corrupted
                processed_videos.remove(video)
                print(f"Removed {file_path} from the list. It's corrupted.")

            file_path = video["VIDEO_PATH"]
            duration = video["VIDEO_DURATION"]

            frame_data = create_keyframes(file_path, duration)

            if frame_data:
                video["KEYFRAMES"] = frame_data

            # Describe the keyframes for each video
            response = describe_keyframes(video)
            message = response.choices[0].message
            message_text = message.content
            print(message_text)

            # Save the message text to the gp-vision-outputs folder
            file_name = os.path.basename(video["VIDEO_PATH"]).split(".")[0]
            file_path = f"{config['gpt_vision_outputs_folder']}/{file_name}.txt"

            # Create the folder if it doesn't exist
            if not os.path.exists(config["gpt_vision_outputs_folder"]):
                os.mkdir(config["gpt_vision_outputs_folder"])

            with open(file_path, "w") as f:
                f.write(message_text)

            # Save the description path to the video object
            video["DESCRIPTION_PATH"] = file_path

        with open(config["json_file_path"], "w") as f:
            json.dump(processed_videos, f, indent=4)
    except Exception as e:
        print(f"Error during video processing: {e}")

    # # update the json file with the new data
    # with open(config["json_file_path"], "w") as f:
    #     json.dump(processed_videos, f, indent=4)
