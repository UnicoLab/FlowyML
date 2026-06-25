/**
 * FlowyML Documentation — Enhanced UX (extra.js)
 * ------------------------------------------------
 * Features:
 *   1. Reading progress bar (gradient, shows after 100px scroll)
 *   2. Enhanced copy-button toast feedback
 *   3. Heading anchor links on h2/h3
 *   4. Smooth scroll for internal anchor links
 */

document.addEventListener("DOMContentLoaded", function () {

  /* ================================================================
     1. Reading Progress Bar
     ================================================================ */
  (function initProgressBar() {
    var bar = document.createElement("div");
    bar.id = "reading-progress";
    bar.style.width = "0%";
    document.body.prepend(bar);

    function updateProgress() {
      var scrollTop = window.scrollY || document.documentElement.scrollTop;
      var docHeight = document.documentElement.scrollHeight - window.innerHeight;

      if (docHeight <= 0) {
        bar.style.width = "0%";
        bar.classList.remove("visible");
        return;
      }

      // Only show bar after scrolling past 100px
      if (scrollTop > 100) {
        bar.classList.add("visible");
      } else {
        bar.classList.remove("visible");
      }

      var progress = Math.min((scrollTop / docHeight) * 100, 100);
      bar.style.width = progress.toFixed(1) + "%";
    }

    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress, { passive: true });
    updateProgress();
  })();


  /* ================================================================
     2. Enhanced Copy Feedback (Toast Notification)
     ================================================================ */
  (function initCopyToast() {
    document.addEventListener("click", function (e) {
      var btn = e.target.closest(".md-clipboard");
      if (!btn) return;

      // Find the parent code block to position the toast
      var codeBlock = btn.closest(".highlight, .md-code__content, pre");
      if (!codeBlock) codeBlock = btn.parentElement;

      // Make sure we have a positioning context
      if (getComputedStyle(codeBlock).position === "static") {
        codeBlock.style.position = "relative";
      }

      // Remove any existing toast in this block
      var existing = codeBlock.querySelector(".copy-toast");
      if (existing) existing.remove();

      var toast = document.createElement("span");
      toast.className = "copy-toast";
      toast.textContent = "Copied! ✓";
      codeBlock.appendChild(toast);

      // Remove the toast after the animation ends (~1.5s)
      setTimeout(function () {
        if (toast.parentNode) toast.remove();
      }, 1600);
    });
  })();


  /* ================================================================
     3. Heading Anchor Links
     ================================================================ */
  (function initHeadingAnchors() {
    var headings = document.querySelectorAll(
      ".md-typeset h2[id], .md-typeset h3[id]"
    );

    headings.forEach(function (heading) {
      // Skip if anchor already exists (e.g. from a plugin)
      if (heading.querySelector(".heading-anchor")) return;

      var anchor = document.createElement("a");
      anchor.className = "heading-anchor";
      anchor.href = "#" + heading.id;
      anchor.setAttribute("aria-label", "Link to this section");
      anchor.textContent = "#";
      heading.appendChild(anchor);
    });
  })();


  /* ================================================================
     4. Smooth Scroll for Internal Anchor Links
     ================================================================ */
  (function initSmoothScroll() {
    document.addEventListener("click", function (e) {
      var link = e.target.closest('a[href^="#"]');
      if (!link) return;

      var targetId = link.getAttribute("href");
      if (!targetId || targetId === "#") return;

      var target;
      try {
        target = document.querySelector(targetId);
      } catch (_) {
        return; // invalid selector
      }

      if (!target) return;

      e.preventDefault();
      var headerOffset = 80; // account for fixed header
      var elementPosition = target.getBoundingClientRect().top + window.scrollY;
      var offsetPosition = elementPosition - headerOffset;

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth"
      });

      // Update URL hash without jumping
      if (history.pushState) {
        history.pushState(null, null, targetId);
      }
    });
  })();

});
