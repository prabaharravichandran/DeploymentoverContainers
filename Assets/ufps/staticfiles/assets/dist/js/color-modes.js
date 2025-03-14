const showActiveTheme = (theme, focus = false) => {
  const themeSwitcher = document.querySelector('#bd-theme');

  if (!themeSwitcher) return;

  const themeSwitcherText = document.querySelector('#bd-theme-text');
  const activeThemeIcon = document.querySelector('.theme-icon-active use');
  const btnToActive = document.querySelector(`[data-bs-theme-value="${theme}"]`);

  if (!btnToActive) {
    console.warn(`No button found with data-bs-theme-value="${theme}"`);
    return;
  }

  const svgUse = btnToActive.querySelector('svg use');
  if (!svgUse) {
    console.warn(`No SVG icon found in button for theme "${theme}"`);
    return;
  }

  const svgOfActiveBtn = svgUse.getAttribute('href');

  document.querySelectorAll('[data-bs-theme-value]').forEach(element => {
    element.classList.remove('active');
    element.setAttribute('aria-pressed', 'false');
  });

  btnToActive.classList.add('active');
  btnToActive.setAttribute('aria-pressed', 'true');

  if (activeThemeIcon) {
    activeThemeIcon.setAttribute('href', svgOfActiveBtn);
  }

  const themeSwitcherLabel = `${themeSwitcherText ? themeSwitcherText.textContent : 'Theme'} (${btnToActive.dataset.bsThemeValue})`;
  themeSwitcher.setAttribute('aria-label', themeSwitcherLabel);

  if (focus) {
    themeSwitcher.focus();
  }
};
