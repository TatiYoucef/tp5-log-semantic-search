const slides = Array.from(document.querySelectorAll(".slide"));
const previousButton = document.querySelector("#prev");
const nextButton = document.querySelector("#next");
const counter = document.querySelector("#counter");

function currentIndexFromHash() {
  const value = Number.parseInt(window.location.hash.replace("#", ""), 10);
  if (Number.isFinite(value) && value >= 1 && value <= slides.length) {
    return value - 1;
  }
  return 0;
}

let current = currentIndexFromHash();

function render() {
  slides.forEach((slide, index) => {
    slide.classList.toggle("active", index === current);
  });
  counter.textContent = `${current + 1} / ${slides.length}`;
  previousButton.disabled = current === 0;
  nextButton.disabled = current === slides.length - 1;
  window.location.hash = String(current + 1);
}

function go(delta) {
  current = Math.min(slides.length - 1, Math.max(0, current + delta));
  render();
}

previousButton.addEventListener("click", () => go(-1));
nextButton.addEventListener("click", () => go(1));

window.addEventListener("keydown", (event) => {
  if (["ArrowRight", "PageDown", " "].includes(event.key)) {
    event.preventDefault();
    go(1);
  }
  if (["ArrowLeft", "PageUp"].includes(event.key)) {
    event.preventDefault();
    go(-1);
  }
  if (event.key === "Home") {
    current = 0;
    render();
  }
  if (event.key === "End") {
    current = slides.length - 1;
    render();
  }
});

window.addEventListener("hashchange", () => {
  current = currentIndexFromHash();
  render();
});

render();
