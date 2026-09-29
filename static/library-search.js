(() => {
    const input = document.getElementById('library-search');
    if (!input) return;
    const cards = [...document.querySelectorAll('#library-grid [data-game-name]')];
    const empty = document.getElementById('library-no-results');
    const normalize = value => value.trim().toLowerCase().normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '').replace(/ı/g, 'i');
    const names = cards.map(card => normalize(card.dataset.gameName));
    function filter() {
        const query = normalize(input.value);
        let count = 0;
        cards.forEach((card, index) => {
            card.hidden = !names[index].includes(query);
            if (!card.hidden) count++;
        });
        empty.hidden = count !== 0;
    }
    input.addEventListener('input', filter);
    input.addEventListener('search', filter);
    window.addEventListener('pageshow', filter);
    filter();
})();
