/**
 * Taskinator Kanban Logic
 * Uses SortableJS for drag-and-drop with server-side sync.
 */

document.addEventListener('DOMContentLoaded', () => {
    const lanes = document.querySelectorAll('.kanban-lane');
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

    function updateCounts() {
        document.querySelectorAll('.kanban-lane').forEach(lane => {
            const status = lane.dataset.status;
            const count = lane.querySelectorAll('.task-card').length;
            const badge = document.getElementById(`count-${status.toLowerCase()}`);
            if (badge) badge.textContent = count;
        });
    }

    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed`;
        toast.style.cssText = 'bottom:20px;right:20px;z-index:9999;min-width:250px;';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // Initialize Sortable for each lane
    lanes.forEach(lane => {
        new Sortable(lane, {
            group: 'tasks',
            animation: 150,
            ghostClass: 'bg-light',
            onEnd: async (evt) => {
                const card = evt.item;
                const taskId = card.dataset.id;
                const currentStatus = card.dataset.currentStatus;
                const newStatus = evt.to.dataset.status;

                if (currentStatus === 'DONE' && newStatus !== 'DONE') {
                    showToast('Tasks in DONE cannot be moved back', 'danger');
                    evt.from.appendChild(card);
                    return;
                }

                const formData = new URLSearchParams();
                formData.append('status', newStatus);
                formData.append('csrf_token', csrfToken);

                try {
                    const response = await fetch(`/tasks/${taskId}/move?ajax=1`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        credentials: 'same-origin',
                        body: formData.toString()
                    });

                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    const data = await response.json();

                    if (data.success) {
                        card.dataset.currentStatus = newStatus;
                        updateCounts();
                        showToast('Status updated');
                    } else {
                        throw new Error(data.error || 'Move failed');
                    }
                } catch (err) {
                    console.error(err);
                    showToast(err.message || 'Error updating task', 'danger');
                    evt.from.appendChild(card);
                }
            }
        });
    });

    updateCounts();
});
