(() => {
    document.querySelectorAll('[data-suggestions-url]').forEach((form, formIndex) => {
        const input = form.querySelector('[name="q"]');
        const type = form.querySelector('[name="type"]');
        const popup = form.querySelector('.suggestion-popup');
        const list = form.querySelector('.suggestion-list');
        const message = form.querySelector('.suggestion-message');
        const status = form.querySelector('.suggestion-status');
        list.id = `search-suggestions-${formIndex}`;
        input.setAttribute('aria-controls', list.id);
        let timer, controller, revision = 0, active = -1, items = [], composing = false;

        function close() {
            clearTimeout(timer);
            controller?.abort();
            revision++;
            popup.hidden = true;
            input.setAttribute('aria-expanded', 'false');
            input.removeAttribute('aria-activedescendant');
            input.removeAttribute('aria-busy');
            list.replaceChildren();
            status.textContent = '';
            items = [];
            active = -1;
        }
        function showMessage(text) {
            message.textContent = text;
            message.hidden = false;
            popup.hidden = false;
            input.setAttribute('aria-expanded', 'true');
            status.textContent = text;
        }
        function select(index) {
            active = index;
            [...list.children].forEach((option, i) => {
                option.setAttribute('aria-selected', String(i === active));
            });
            const option = list.children[active];
            if (option) {
                input.setAttribute('aria-activedescendant', option.id);
                option.scrollIntoView({block: 'nearest'});
            } else {
                input.removeAttribute('aria-activedescendant');
            }
        }
        async function load(query, mode, ticket) {
            controller = new AbortController();
            showMessage(form.dataset.loading);
            input.setAttribute('aria-busy', 'true');
            try {
                const url = new URL(form.dataset.suggestionsUrl, window.location.origin);
                url.search = new URLSearchParams({q: query, type: mode});
                const response = await fetch(url, {signal: controller.signal});
                if (!response.ok) throw new Error('Search unavailable');
                const data = await response.json();
                if (ticket !== revision) return;
                items = data.results.slice(0, 5);
                if (!items.length) {
                    showMessage(form.dataset.empty);
                    return;
                }
                message.hidden = true;
                items.forEach((item, index) => {
                    const option = document.createElement('li');
                    option.id = `${list.id}-${index}`;
                    option.setAttribute('role', 'option');
                    option.setAttribute('aria-selected', 'false');
                    if (item.image) {
                        const image = document.createElement('img');
                        image.src = item.image;
                        image.alt = '';
                        image.addEventListener('error', () => image.remove(), {once: true});
                        option.append(image);
                    }
                    const name = document.createElement('span');
                    name.textContent = item.name;
                    option.append(name);
                    option.addEventListener('pointerdown', e => e.preventDefault());
                    option.addEventListener('click', () => window.location.assign(item.url));
                    list.append(option);
                });
                status.textContent = form.dataset.count.replace('{count}', String(items.length));
            } catch (error) {
                if (ticket === revision && error.name !== 'AbortError') showMessage(form.dataset.error);
            } finally {
                if (ticket === revision) input.removeAttribute('aria-busy');
            }
        }
        function schedule() {
            close();
            const query = input.value.trim();
            if (composing || query.length < 3) return;
            const ticket = revision;
            const mode = type.value;
            timer = setTimeout(() => load(query, mode, ticket), 350);
        }
        input.addEventListener('input', schedule);
        input.addEventListener('focus', schedule);
        input.addEventListener('compositionstart', () => { composing = true; close(); });
        input.addEventListener('compositionend', () => { composing = false; schedule(); });
        type.addEventListener('change', () => { input.focus(); schedule(); });
        input.addEventListener('keydown', event => {
            if (event.isComposing) return;
            if (event.key === 'Escape') { event.preventDefault(); close(); }
            else if (!popup.hidden && items.length && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
                event.preventDefault();
                select(event.key === 'ArrowDown' ? (active + 1) % items.length : (active <= 0 ? items.length - 1 : active - 1));
            } else if (event.key === 'Enter' && !popup.hidden && active >= 0) {
                event.preventDefault();
                window.location.assign(items[active].url);
            }
        });
        form.addEventListener('submit', close);
        form.addEventListener('focusout', () => {
            setTimeout(() => { if (!form.contains(document.activeElement)) close(); }, 0);
        });
        document.addEventListener('pointerdown', event => { if (!form.contains(event.target)) close(); });
        window.addEventListener('pagehide', close);
    });
})();
