/**
 * Taskinator Kanban Logic
 * Framework: Alpine.js + SortableJS
 */

document.addEventListener('DOMContentLoaded', () => {
    const lanes = document.querySelectorAll('.kanban-lane');
    
    // Initialize Sortable for each lane
    lanes.forEach(lane => {
        new Sortable(lane, {
            group: 'tasks',
            animation: 150,
            ghostClass: 'bg-light',
            onEnd: async (evt) => {
                const taskId = evt.item.dataset.id;
                const newStatus = evt.to.dataset.status;
                
                try {
                    const response = await fetch(`/api/tasks/${taskId}/move`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: newStatus })
                    });
                    
                    if (!response.ok) throw new Error('Failed to move task');
                    console.log(`Task ${taskId} moved to ${newStatus}`);
                } catch (err) {
                    console.error(err);
                    alert('Error updating task status. Reverting...');
                    evt.item.classList.add('bg-danger'); // Visual error
                    // Simple revert: move back to original lane
                    evt.from.appendChild(evt.item);
                }
            }
        });
    });

    // Load Tasks from API
    async function loadTasks() {
        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            
            // Clear lanes
            lanes.forEach(l => l.innerHTML = '');
            
            tasks.forEach(task => {
                const lane = document.querySelector(`.kanban-lane[data-status="${task.status}"]`);
                if (lane) {
                    lane.appendChild(createTaskCard(task));
                }
            });
            
            updateCounts();
        } catch (err) {
            console.error('Failed to load tasks:', err);
        }
    }

    function createTaskCard(task) {
        const div = document.createElement('div');
        div.className = 'card mb-2 shadow-sm task-card';
        div.dataset.id = task.id;
        
        const priorityClass = {
            'high': 'text-danger',
            'medium': 'text-warning',
            'low': 'text-muted'
        }[task.priority] || '';

        const categoryClass = {
            'feature': 'bg-primary',
            'bug': 'bg-danger',
            'improvement': 'bg-success',
            'tech-debt': 'bg-info'
        }[task.category] || 'bg-secondary';

        div.innerHTML = `
            <div class="card-body p-2">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <span class="badge ${categoryClass}" style="font-size: 0.7rem">${task.category}</span>
                    <small class="${priorityClass} fw-bold">${task.priority.toUpperCase()}</small>
                </div>
                <h6 class="card-title small mb-1">${task.title}</h6>
                <p class="card-text text-muted" style="font-size: 0.75rem">${task.description.substring(0, 60)}${task.description.length > 60 ? '...' : ''}</p>
                <div class="d-flex justify-content-end">
                    <button class="btn btn-sm btn-light text-dark" onclick="openEditModal(${task.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                </div>
            </div>
        `;
        return div;
    }

    function updateCounts() {
        document.querySelectorAll('.kanban-lane').forEach(lane => {
            const status = lane.dataset.status;
            const count = lane.children.length;
            document.getElementById(`count-${status}`).innerText = count;
        });
    }

    // Add Task Event
    document.getElementById('btn-save-task')?.addEventListener('click', async () => {
        const form = document.getElementById('form-add-task');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (response.ok) {
                const newTask = await response.json();
                loadTasks(); // Refresh board
                bootstrap.Modal.getInstance(document.getElementById('modal-add-task')).hide();
                form.reset();
            }
        } catch (err) {
            alert('Error saving task');
        }
    });

    loadTasks();
});
