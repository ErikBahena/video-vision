const download_path = '/Users/erikbahena/Downloads';

function generateUUID() {
  let d = new Date().getTime();
  let d2 = (performance && performance.now && performance.now() * 1000) || 0;
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    let r = Math.random() * 16;
    if (d > 0) {
      r = (d + r) % 16 | 0;
      d = Math.floor(d / 16);
    } else {
      r = (d2 + r) % 16 | 0;
      d2 = Math.floor(d2 / 16);
    }
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function formatViews(viewsStr) {
  if (viewsStr.includes('M')) {
    return parseInt(parseFloat(viewsStr.replace('M', '')) * 1000000);
  } else if (viewsStr.includes('K')) {
    return parseInt(parseFloat(viewsStr.replace('K', '')) * 1000);
  } else {
    return parseInt(viewsStr);
  }
}

async function gatherTikTokData(maxVideos = 10) {
  // Select the main container at data-e2e="search_video-item-list"
  const mainContainer = document.querySelector(
    '[data-e2e="search_video-item-list"]',
  );

  if (!mainContainer) {
    console.error('Unable to find main container!');
    return [];
  }

  // Get all video cards starting from the third child also use the maxVideos parameter
  const videoCards = Array.from(mainContainer.children)
    .slice(2)
    .slice(0, maxVideos);
  const videos = [];

  for (let i = 0; i < videoCards.length; i++) {
    const videoCard = videoCards[i];
    // Extract VIEWS
    const videoCountElement = videoCard.querySelector(
      '[class*="-StrongVideoCount"]',
    );
    const VIDEO_VIEWS = videoCountElement
      ? formatViews(videoCountElement.textContent.trim())
      : null;

    // Extract Title of the div with  -DivMetaCaptionLine in it's class then find the first span child
    const videoTitleElement = videoCard.querySelector(
      '[class*="-DivMetaCaptionLine"] > div > span',
    );

    const VIDEO_TITLE = videoTitleElement
      ? videoTitleElement.textContent.trim()
        ? videoTitleElement.textContent.trim()
        : null
      : null;

    // Extract VIDEO_LINK
    const videoLinkElement = videoCard.querySelector(
      'a[href*="https://www.tiktok.com"]',
    );

    const VIDEO_LINK = videoLinkElement ? videoLinkElement.href : null;

    if (VIDEO_LINK) {
      const VIDEO_PATH = await downloadVideo(VIDEO_LINK);

      videos.push({
        VIDEO_TITLE,
        VIDEO_VIEWS,
        VIDEO_LINK,
        VIDEO_PATH,
      });
    } else {
      console.error('Unable to find video link!');
    }
  }

  return videos;
}

function saveJSON(data, filename) {
  if (!data) {
    console.error('No data provided');
    return;
  }

  if (!filename) {
    console.error('No filename provided');
    return;
  }

  const blob = new Blob([JSON.stringify(data, null, 4)], { type: 'text/json' });
  const e = document.createEvent('MouseEvents');
  const a = document.createElement('a');

  a.download = filename;
  a.href = window.URL.createObjectURL(blob);
  a.dataset.downloadurl = ['text/json', a.download, a.href].join(':');
  e.initMouseEvent(
    'click',
    true,
    false,
    window,
    0,
    0,
    0,
    0,
    0,
    false,
    false,
    false,
    false,
    0,
    null,
  );
  a.dispatchEvent(e);
}

async function downloadVideo(videoLink) {
  // Open the video link in a new tab
  const videoTab = window.open(videoLink, '_blank');

  // Wait for a few seconds (adjust the timeout as needed)
  await new Promise((resolve) => setTimeout(resolve, 3000));

  const videoElement = videoTab.document.querySelector('video');

  if (videoElement) {
    // get the video source
    const videoSource = videoElement.src;

    // Open the video source in a new tab
    const videoSourceTab = window.open(videoSource, '_blank');

    // Wait for a few seconds (adjust the timeout as needed)
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // download the video
    const blob = await fetch(videoSource).then((response) => response.blob());

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = `${generateUUID()}.mp4`;

    a.click();
    window.URL.revokeObjectURL(url);

    videoSourceTab.close();
    videoTab.close();

    return `${download_path}/${a.download}`;
  }

  videoTab.close();
}

async function main() {
  const output_data_file_name = 'top_videos.json';
  const max_videos = 10;

  let raw_data = await gatherTikTokData(max_videos);

  if (raw_data.length === 0) {
    console.error('No data was gathered!');
    return;
  }

  saveJSON(raw_data, output_data_file_name);
}

main();
