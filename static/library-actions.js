(() => {
    document.querySelectorAll('.action-toast').forEach(toast => {
        let timer;
        const dismiss = () => toast.remove();
        const schedule = () => { clearTimeout(timer); timer = setTimeout(dismiss, 15000); };
        toast.querySelector('.toast-dismiss').addEventListener('click', dismiss);
        toast.addEventListener('pointerenter', () => clearTimeout(timer));
        toast.addEventListener('pointerleave', () => { if (!toast.contains(document.activeElement)) schedule(); });
        toast.addEventListener('focusin', () => clearTimeout(timer));
        toast.addEventListener('focusout', schedule);
        schedule();
    });

    document.querySelectorAll('.note-toggle').forEach(button => {
        const note = document.getElementById(button.getAttribute('aria-controls'));
        note.classList.add('note-collapsed');
        const measure = () => {
            if (!note.getClientRects().length || button.getAttribute('aria-expanded') === 'true') return;
            button.hidden = note.scrollHeight <= note.clientHeight + 1;
            button.closest('.library-card-meta').classList.toggle('has-note-toggle', !button.hidden);
        };
        button.addEventListener('click', () => {
            const expanded = button.getAttribute('aria-expanded') !== 'true';
            button.setAttribute('aria-expanded', String(expanded));
            button.textContent = expanded ? button.dataset.less : button.dataset.more;
            note.classList.toggle('note-collapsed', !expanded);
            measure();
        });
        if (window.ResizeObserver) new ResizeObserver(measure).observe(note);
        window.addEventListener('resize', measure);
        if (document.fonts) document.fonts.ready.then(measure);
        measure();
    });

    document.querySelectorAll('.quick-add-form').forEach(form => {
        form.addEventListener('submit', async event => {
            event.preventDefault();
            const button = form.querySelector('button');
            if (button.disabled) return;
            const original = button.textContent;
            const feedback = form.querySelector('.quick-add-feedback');
            button.disabled = true;
            button.textContent = form.dataset.adding;
            feedback.textContent = '';
            try {
                const response = await fetch(form.action, {method: 'POST', body: new FormData(form), headers: {Accept: 'application/json'}});
                const data = await response.json();
                if (!response.ok || !data.ok) throw new Error('Add failed');
                button.textContent = data.message;
                const card = form.closest('.game-card');
                const hint = card.querySelector('.search-card-hint');
                hint.textContent = form.dataset.owned;
                hint.classList.add('search-card-hint-owned');
                if (!card.querySelector('.badge-owned')) {
                    const badge = document.createElement('span');
                    badge.className = 'badge-owned';
                    badge.textContent = '✓';
                    card.querySelector('.game-card-media').append(badge);
                }
            } catch {
                button.disabled = false;
                button.textContent = original;
                feedback.textContent = form.dataset.error;
            }
        });
    });
})();
