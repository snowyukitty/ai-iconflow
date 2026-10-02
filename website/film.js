// Film: the cover is one button. Playing starts from that gesture (iOS needs
// play() inside it), captions follow the page language, and the film ends on
// its last frame with a way to watch again or start, never an autoplay loop.
const film = document.querySelector('[data-film]');
if (film) {
  const video = film.querySelector('[data-film-video]');
  const cover = film.querySelector('[data-film-play]');
  const end = film.querySelector('[data-film-end]');
  const pageLang = (document.documentElement.lang || 'en').toLowerCase();
  let captionsPicked = false;               // after the first play the viewer's own choice wins
  const pickCaptions = () => {
    if (captionsPicked) return;
    captionsPicked = true;
    const tracks = [...video.textTracks];
    const match = tracks.find((t) => t.language.toLowerCase() === pageLang)
      || tracks.find((t) => t.language.toLowerCase().split('-')[0] === pageLang.split('-')[0])
      || tracks.find((t) => t.language === 'en');
    tracks.forEach((t) => { t.mode = t === match ? 'showing' : 'disabled'; });
  };
  const start = () => {
    film.classList.add('is-playing');
    end.hidden = true;
    pickCaptions();
    const playing = video.play();
    if (playing) playing.catch(() => { /* blocked or failed: native controls stay usable */ });
    video.focus({ preventScroll: true });
  };
  cover.addEventListener('click', start);
  video.addEventListener('play', () => { film.classList.add('is-playing'); end.hidden = true; });
  // The film fades to black; hold its composed end card instead of the black frame.
  video.addEventListener('ended', () => {
    if (Number.isFinite(video.duration)) video.currentTime = Math.max(0, video.duration - 1.6);
    end.hidden = false;
  });
  film.querySelector('[data-film-replay]')?.addEventListener('click', () => { video.currentTime = 0; start(); });
}
