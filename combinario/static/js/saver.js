(function () {
  const STORAGE_KEY = "combinario_sidenav_items";

  function saveItems() {
    const items = [];
    document
      .querySelectorAll(".sidenav .items-container .item")
      .forEach((item) => {
        items.push({
          id: item.getAttribute("item-id"),
          text: item.getAttribute("item-text"),
          emoji: item.getAttribute("item-emoji"),
        });
      });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }

  function setItemContent(element, emoji, text) {
    element.textContent = "";

    const emojiSpan = document.createElement("span");
    emojiSpan.className = "item-emoji";
    emojiSpan.textContent = emoji;

    element.appendChild(emojiSpan);
    element.appendChild(document.createTextNode(" " + text));
  }

  function loadItems() {
    const savedData = localStorage.getItem(STORAGE_KEY);
    if (!savedData) return;

    const items = JSON.parse(savedData);
    const itemsContainer = document.querySelector(".sidenav .items-container");
    if (!itemsContainer) return;

    itemsContainer.innerHTML = "";

    items.forEach((item) => {
      const div = document.createElement("div");
      div.className = "item";
      div.setAttribute("draggable", "true");
      div.setAttribute("item-id", item.id);
      div.setAttribute("item-emoji", item.emoji);
      div.setAttribute("item-text", item.text);

      setItemContent(div, item.emoji, item.text);

      if (window.ItemManager) {
        div.addEventListener("mousedown", (e) =>
          window.ItemManager.handleSidebarMouseDown(e),
        );
        div.addEventListener("click", (e) =>
          window.ItemManager.handleSidebarClick(e),
        );
      }

      itemsContainer.appendChild(div);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadItems);
  } else {
    loadItems();
  }

  const observer = new MutationObserver(saveItems);
  const itemsContainer = document.querySelector(".sidenav .items-container");
  if (itemsContainer) {
    observer.observe(itemsContainer, { childList: true });
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      const container = document.querySelector(".sidenav .items-container");
      if (container) observer.observe(container, { childList: true });
    });
  }
})();
