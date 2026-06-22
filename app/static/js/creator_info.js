/**
 * creator_info.js – Creator Contact Info modal handler.
 *
 * Initialised automatically on DOMContentLoaded when the
 * #creator-modal and #creator-info-btn elements are present.
 */
(function () {
  'use strict';

  function init() {
    var modal     = document.getElementById('creator-modal');
    var openBtn   = document.getElementById('creator-info-btn');
    var closeBtn  = document.querySelector('#creator-modal .close-btn');

    if (!modal || !openBtn) return;

    function openModal() {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
      if (closeBtn) closeBtn.focus();
    }

    function closeModal() {
      modal.classList.remove('active');
      document.body.style.overflow = '';
      openBtn.focus();
    }

    openBtn.addEventListener('click', openModal);

    if (closeBtn) {
      closeBtn.addEventListener('click', closeModal);
    }

    // Close when clicking the backdrop
    modal.addEventListener('click', function (e) {
      if (e.target === modal) closeModal();
    });

    // Close on Escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('active')) {
        closeModal();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
