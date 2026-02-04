class ItemManager {
  constructor(workspaceSelector = ".workspace", sidenavSelector = ".sidenav") {
    this.CONFIG = {
      ITEM_WIDTH: 120,
      ITEM_HEIGHT: 38,
      SPACING: 140,
      DEBOUNCE_MS: 150,
      POLL_INTERVAL: 1000,
    };

    this.isDragging = false;
    this.hasDragged = false;
    this.currentDraggedItem = null;
    this.offsetX = 0;
    this.offsetY = 0;
    this.allSpawnedItems = new Set();
    this.pendingJobs = new Map();

    this.workspaceSelector = workspaceSelector;
    this.sidenavSelector = sidenavSelector;
    this.workspace = null;
    this.sidenav = null;

    this.handleMouseMove = this.handleMouseMove.bind(this);
    this.handleMouseUp = this.handleMouseUp.bind(this);
  }

  debounce(fn, ms) {
    let timeout;
    return function (...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn(...args), ms);
    };
  }

  clamp(val, min, max) {
    return Math.min(Math.max(val, min), max);
  }

  isOverlapping(rect1, rect2) {
    return !(
      rect1.right < rect2.left ||
      rect1.left > rect2.right ||
      rect1.bottom < rect2.top ||
      rect1.top > rect2.bottom
    );
  }

  async combineItems(firstId, secondId) {
    try {
      const response = await fetch(`/items/${firstId}/${secondId}`);
      const data = await response.json();

      if (data.enqueued) {
        return { jobId: data.enqueued };
      } else {
        return { item: data };
      }
    } catch (error) {
      console.error("Error combining items:", error);
      return null;
    }
  }

  async pollJob(jobId) {
    try {
      const response = await fetch(`/task/${jobId}`);
      const data = await response.json();

      if (data.status === "complete") {
        return { done: true, item: data.result };
      } else if (data.status === "failed") {
        return { done: true, error: true };
      } else {
        return { done: false };
      }
    } catch (error) {
      console.error("Error polling job:", error);
      return { done: true, error: true };
    }
  }

  startPolling(jobId, placeholder) {
    this.pendingJobs.set(jobId, placeholder);

    const pollInterval = setInterval(async () => {
      const result = await this.pollJob(jobId);

      if (result.done) {
        clearInterval(pollInterval);
        this.pendingJobs.delete(jobId);

        if (result.error) {
          placeholder.textContent = "❌ Error";
          placeholder.style.borderColor = "red";
        } else if (result.item) {
          placeholder.innerHTML = `<span class="item-emoji">${result.item.emoji}</span> ${result.item.text}`;
          placeholder.setAttribute("item-id", result.item.id);
          placeholder.setAttribute("item-emoji", result.item.emoji);
          placeholder.setAttribute("item-text", result.item.text);
          placeholder.style.borderColor = "";

          this.addToSidebar(result.item);
        }
      }
    }, this.CONFIG.POLL_INTERVAL);
  }

  findNearbyEmptyPosition() {
    const workspaceRect = this.workspace.getBoundingClientRect();
    let avgX = 0,
      avgY = 0,
      count = 0;

    this.allSpawnedItems.forEach((item) => {
      if (this.workspace.contains(item)) {
        const rect = item.getBoundingClientRect();
        avgX += rect.left;
        avgY += rect.top;
        count++;
      }
    });

    if (count === 0) {
      return {
        x: workspaceRect.width / 2 - 60,
        y: workspaceRect.height / 2 - 19,
      };
    }

    avgX /= count;
    avgY /= count;

    for (let attempt = 0; attempt < 50; attempt++) {
      const angle = attempt * 137.5 * (Math.PI / 180);
      const radius = Math.sqrt(attempt) * this.CONFIG.SPACING;

      const testX = this.clamp(
        avgX + Math.cos(angle) * radius,
        workspaceRect.left,
        workspaceRect.right - this.CONFIG.ITEM_WIDTH,
      );
      const testY = this.clamp(
        avgY + Math.sin(angle) * radius,
        workspaceRect.top,
        workspaceRect.bottom - this.CONFIG.ITEM_HEIGHT,
      );

      const testRect = {
        left: testX,
        right: testX + this.CONFIG.ITEM_WIDTH,
        top: testY,
        bottom: testY + this.CONFIG.ITEM_HEIGHT,
      };

      let overlaps = false;
      for (let item of this.allSpawnedItems) {
        if (
          this.workspace.contains(item) &&
          this.isOverlapping(testRect, item.getBoundingClientRect())
        ) {
          overlaps = true;
          break;
        }
      }

      if (!overlaps)
        return { x: testX - workspaceRect.left, y: testY - workspaceRect.top };
    }

    return {
      x: avgX - workspaceRect.left + this.CONFIG.SPACING,
      y: avgY - workspaceRect.top,
    };
  }

  checkCollisions(draggedItem) {
    if (!this.workspace.contains(draggedItem)) return;

    const draggedRect = draggedItem.getBoundingClientRect();
    const itemsArray = Array.from(this.allSpawnedItems);
    let hasCollision = false;

    for (let item of itemsArray) {
      if (item === draggedItem || !this.workspace.contains(item)) continue;

      if (this.isOverlapping(draggedRect, item.getBoundingClientRect())) {
        hasCollision = true;

        draggedItem.style.borderColor = "white";
        draggedItem.style.transform = "scale(1.1)";
        item.style.borderColor = "white";
        item.style.transform = "scale(0.95)";

        const itemRect = item.getBoundingClientRect();

        const workspaceRect = this.workspace.getBoundingClientRect();
        const placeholderX = itemRect.left - workspaceRect.left;
        const placeholderY = itemRect.top - workspaceRect.top;

        const firstId = parseInt(draggedItem.getAttribute("item-id"));
        const secondId = parseInt(item.getAttribute("item-id"));

        this.allSpawnedItems.delete(draggedItem);
        this.allSpawnedItems.delete(item);
        draggedItem.remove();
        item.remove();

        const placeholder = document.createElement("div");
        placeholder.className = "item spawned-item";
        placeholder.textContent = "⏳ Loading...";
        placeholder.style.cssText = `position:absolute;left:${placeholderX}px;top:${placeholderY}px;width:${this.CONFIG.ITEM_WIDTH}px;cursor:move;transition:border-color 0.2s, transform 0.2s`;
        placeholder.dataset.initialized = "true";

        this.workspace.appendChild(placeholder);
        this.allSpawnedItems.add(placeholder);
        this.makeSpawnedItemDraggable(placeholder);

        this.combineItems(firstId, secondId).then((result) => {
          if (result.jobId) {
            this.startPolling(result.jobId, placeholder);
          } else if (result.item) {
            placeholder.innerHTML = `<span class="item-emoji">${result.item.emoji}</span> ${result.item.text}`;
            placeholder.setAttribute("item-id", result.item.id);
            placeholder.setAttribute("item-emoji", result.item.emoji);
            placeholder.setAttribute("item-text", result.item.text);

            this.addToSidebar(result.item);
          } else {
            placeholder.textContent = "❌ Error";
            placeholder.style.borderColor = "red";
          }
        });

        break;
      }
    }

    if (!hasCollision) {
      draggedItem.style.borderColor = "";
      draggedItem.style.transform = "";
    }
  }

  addToSidebar(item) {
    const existingItem = document.querySelector(
      `${this.sidenavSelector} .item[item-id="${item.id}"]`,
    );

    if (existingItem) {
      return;
    }

    const sidebarItem = document.createElement("div");
    sidebarItem.className = "item";
    sidebarItem.setAttribute("draggable", "true");
    sidebarItem.setAttribute("item-id", item.id);
    sidebarItem.setAttribute("item-emoji", item.emoji);
    sidebarItem.setAttribute("item-text", item.text);
    sidebarItem.innerHTML = `<span class="item-emoji">${item.emoji}</span> ${item.text}`;

    sidebarItem.addEventListener("mousedown", (e) =>
      this.handleSidebarMouseDown(e),
    );
    sidebarItem.addEventListener("click", (e) => this.handleSidebarClick(e));

    const itemsContainer = document.querySelector(
      `${this.sidenavSelector} .items-container`,
    );
    if (itemsContainer) {
      itemsContainer.appendChild(sidebarItem);

      sidebarItem.style.animation = "fadeIn 0.3s ease-in";
    }
  }

  handleMouseMove(e) {
    if (!this.isDragging || !this.currentDraggedItem) return;

    this.hasDragged = true;
    this.currentDraggedItem.style.left = e.clientX - this.offsetX + "px";
    this.currentDraggedItem.style.top = e.clientY - this.offsetY + "px";

    this.checkCollisionPreview(this.currentDraggedItem);
  }

  checkCollisionPreview(draggedItem) {
    const draggedRect = draggedItem.getBoundingClientRect();
    let hasCollision = false;

    this.allSpawnedItems.forEach((item) => {
      if (item === draggedItem || !this.workspace.contains(item)) return;

      if (this.isOverlapping(draggedRect, item.getBoundingClientRect())) {
        hasCollision = true;
        draggedItem.style.borderColor = "white";
        draggedItem.style.transform = "scale(1.1)";
        item.style.borderColor = "white";
        item.style.transform = "scale(0.95)";
      } else {
        item.style.borderColor = "";
        item.style.transform = "";
      }
    });

    if (!hasCollision) {
      draggedItem.style.borderColor = "";
      draggedItem.style.transform = "";
    }
  }

  handleMouseUp(e) {
    if (!this.isDragging || !this.currentDraggedItem) return;

    const itemToCheck = this.currentDraggedItem;

    if (!this.hasDragged) {
      this.currentDraggedItem.remove();
      this.cleanup();
      return;
    }

    const sidenavRect = this.sidenav?.getBoundingClientRect();
    const itemRect = this.currentDraggedItem.getBoundingClientRect();
    const droppedOnSidebar =
      sidenavRect &&
      ((e.clientX >= sidenavRect.left &&
        e.clientX <= sidenavRect.right &&
        e.clientY >= sidenavRect.top &&
        e.clientY <= sidenavRect.bottom) ||
        this.isOverlapping(itemRect, sidenavRect));

    if (droppedOnSidebar) {
      this.currentDraggedItem.remove();
      this.allSpawnedItems.delete(this.currentDraggedItem);
    } else {
      const itemRect = this.currentDraggedItem.getBoundingClientRect();
      const workspaceRect = this.workspace.getBoundingClientRect();

      this.workspace.appendChild(this.currentDraggedItem);
      this.currentDraggedItem.style.left =
        itemRect.left - workspaceRect.left + "px";
      this.currentDraggedItem.style.top =
        itemRect.top - workspaceRect.top + "px";
      this.currentDraggedItem.style.zIndex = "";
      this.currentDraggedItem.style.pointerEvents = "auto";

      if (!this.currentDraggedItem.dataset.initialized) {
        this.currentDraggedItem.dataset.initialized = "true";
        this.currentDraggedItem.style.transition =
          "border-color 0.2s, transform 0.2s";
        this.makeSpawnedItemDraggable(this.currentDraggedItem);
      }
      this.allSpawnedItems.add(this.currentDraggedItem);
      this.checkCollisions(itemToCheck);
    }

    this.cleanup();
  }

  cleanup() {
    if (this.currentDraggedItem) {
      this.currentDraggedItem.style.transition =
        "border-color 0.2s, transform 0.2s";
      this.currentDraggedItem.style.zIndex = "";
    }
    this.isDragging = false;
    this.hasDragged = false;
    this.currentDraggedItem = null;
    document.removeEventListener("mousemove", this.handleMouseMove);
    document.removeEventListener("mouseup", this.handleMouseUp);
  }

  handleSidebarClick(e) {
    if (this.isDragging) return;
    e.preventDefault();

    const workspaceRect = this.workspace.getBoundingClientRect();
    const pos =
      this.allSpawnedItems.size === 0
        ? { x: workspaceRect.width / 2 - 60, y: workspaceRect.height / 2 - 19 }
        : this.findNearbyEmptyPosition();

    const clone = e.currentTarget.cloneNode(true);
    clone.className = "item spawned-item";
    clone.style.cssText = `position:absolute;left:${pos.x}px;top:${pos.y}px;width:${this.CONFIG.ITEM_WIDTH}px;cursor:move;transition:border-color 0.2s, transform 0.2s;margin:0;padding:12px 15px;box-sizing:border-box`;
    clone.dataset.initialized = "true";

    this.workspace?.appendChild(clone);
    this.allSpawnedItems.add(clone);
    this.makeSpawnedItemDraggable(clone);
  }

  handleSidebarMouseDown(e) {
    e.preventDefault();
    this.hasDragged = false;

    const clone = e.currentTarget.cloneNode(true);
    clone.className = "item spawned-item";
    clone.style.cssText = `position:absolute;left:${e.clientX - 60}px;top:${e.clientY - 19}px;width:${this.CONFIG.ITEM_WIDTH}px;cursor:move;pointer-events:none;z-index:1000`;

    document.body.appendChild(clone);
    this.currentDraggedItem = clone;
    this.offsetX = 60;
    this.offsetY = 19;
    this.isDragging = true;

    document.addEventListener("mousemove", this.handleMouseMove);
    document.addEventListener("mouseup", this.handleMouseUp);
  }

  makeSpawnedItemDraggable(item) {
    item.addEventListener("mousedown", (e) => {
      e.preventDefault();

      item.style.transition = "none";

      item.style.transform = "";
      item.style.borderColor = "";

      const rect = item.getBoundingClientRect();
      const workspaceRect = this.workspace.getBoundingClientRect();

      document.body.appendChild(item);

      item.style.left = rect.left + "px";
      item.style.top = rect.top + "px";
      item.style.zIndex = "1000";

      this.offsetX = e.clientX - rect.left;
      this.offsetY = e.clientY - rect.top;
      this.currentDraggedItem = item;
      this.isDragging = true;
      document.addEventListener("mousemove", this.handleMouseMove);
      document.addEventListener("mouseup", this.handleMouseUp);
    });
  }

  init() {
    this.workspace = document.querySelector(this.workspaceSelector);
    this.sidenav = document.querySelector(this.sidenavSelector);

    if (!this.workspace) {
      console.error("Workspace element not found");
      return;
    }

    document
      .querySelectorAll(`${this.sidenavSelector} .item`)
      .forEach((item) => {
        item.addEventListener("mousedown", (e) =>
          this.handleSidebarMouseDown(e),
        );
        item.addEventListener("click", (e) => this.handleSidebarClick(e));
      });

    const searchInput = document.querySelector('.searchbar input[type="text"]');
    if (searchInput) {
      searchInput.addEventListener(
        "input",
        this.debounce((e) => {
          const term = e.target.value.toLowerCase();
          document
            .querySelectorAll(`${this.sidenavSelector} .item`)
            .forEach((item) => {
              item.style.display = item.textContent.toLowerCase().includes(term)
                ? "flex"
                : "none";
            });
        }, this.CONFIG.DEBOUNCE_MS),
      );
    }

    setInterval(() => {
      const stale = [];
      this.allSpawnedItems.forEach((item) => {
        if (!this.workspace.contains(item)) stale.push(item);
      });
      stale.forEach((item) => this.allSpawnedItems.delete(item));
    }, 60000);
  }

  clearAll() {
    this.allSpawnedItems.forEach((item) => item.remove());
    this.allSpawnedItems.clear();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    window.ItemManager = new ItemManager();
    window.ItemManager.init();
  });
} else {
  window.ItemManager = new ItemManager();
  window.ItemManager.init();
}
