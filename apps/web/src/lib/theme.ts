// Thème du site public (clair / sombre / automatique), mémorisé dans le navigateur.
export const THEME_KEY = "lds-theme";

/** Script exécuté avant l'affichage : pas d'éclair blanc pour qui a choisi le sombre. */
export const THEME_SCRIPT = `try{var t=localStorage.getItem('${THEME_KEY}')||'auto';var d=t==='dark'||(t==='auto'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('public-dark',d)}catch(e){}`;
