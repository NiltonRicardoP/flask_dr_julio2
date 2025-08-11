document.addEventListener("DOMContentLoaded", function() {
    const serviceCards = document.querySelectorAll('.servico');

    serviceCards.forEach(card => {
        card.addEventListener('mouseover', function() {
            this.style.transform = 'translateY(-10px)';
        });
        card.addEventListener('mouseout', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});
