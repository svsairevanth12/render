// Form generation and management
document.addEventListener('DOMContentLoaded', function() {
    const formBuilder = {
        init() {
            this.bindEvents();
            this.setupFormIfEditing();
            this.setupFieldModal();
            this.setupSpeechRecognition();
        },

        bindEvents() {
            // AI Generation button
            const generateBtn = document.getElementById('generate-form-btn');
            if (generateBtn) {
                generateBtn.addEventListener('click', this.handleGenerate.bind(this));
            }

            // Save form button
            const saveBtn = document.getElementById('save-form-btn');
            if (saveBtn) {
                saveBtn.addEventListener('click', this.handleSave.bind(this));
            }

            // Preview button
            const previewBtn = document.getElementById('preview-form-btn');
            if (previewBtn) {
                previewBtn.addEventListener('click', this.handlePreview.bind(this));
            }

            // Add field button
            const addFieldBtn = document.getElementById('add-field-btn');
            if (addFieldBtn) {
                addFieldBtn.addEventListener('click', () => {
                    this.showFieldModal();
                });
            }
        },

        setupFieldModal() {
            // Field type change handler
            const fieldType = document.getElementById('field-type');
            const optionsContainer = document.getElementById('options-container');
            
            fieldType.addEventListener('change', () => {
                const showOptions = ['select', 'radio', 'checkbox'].includes(fieldType.value);
                optionsContainer.style.display = showOptions ? 'block' : 'none';
            });

            // Add option button
            const addOptionBtn = document.getElementById('add-option-btn');
            addOptionBtn.addEventListener('click', () => {
                this.addOptionInput();
            });

            // Save field button
            const saveFieldBtn = document.getElementById('save-field-btn');
            saveFieldBtn.addEventListener('click', () => {
                this.saveField();
            });

            // Add speech recognition to field label input
            const fieldLabelInput = document.getElementById('field-label');
            this.addSpeechInput(fieldLabelInput);
        },

        setupFormIfEditing() {
            if (window.formData) {
                this.populateForm(window.formData);
            }
        },

        async handleGenerate(e) {
            e.preventDefault();
            const description = document.getElementById('form-description').value.trim();
            
            if (!description) {
                this.showError('Please enter a form description');
                return;
            }

            try {
                this.showLoading('Generating form...');
                const response = await fetch('/generate-form', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ description })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Failed to generate form');
                }

                this.populateFormFields(data.fields);
                this.hideLoading();
                this.showSuccess('Form generated successfully');
            } catch (error) {
                console.error('Error generating form:', error);
                this.hideLoading();
                this.showError(error.message || 'Error generating form');
            }
        },

        async handleSave(e) {
            e.preventDefault();
            const formData = this.collectFormData();
            
            if (!this.validateForm(formData)) {
                return;
            }

            try {
                this.showLoading('Saving form...');
                const response = await fetch('/forms', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Failed to save form');
                }

                this.hideLoading();
                this.showSuccess('Form saved successfully');
                window.location.href = '/forms/' + data.id;
            } catch (error) {
                console.error('Error saving form:', error);
                this.hideLoading();
                this.showError(error.message || 'Error saving form');
            }
        },

        handlePreview(e) {
            e.preventDefault();
            const formData = this.collectFormData();
            
            if (!this.validateForm(formData)) {
                return;
            }

            // Store form data in localStorage for preview
            localStorage.setItem('preview_form', JSON.stringify(formData));
            window.open('/preview', '_blank');
        },

        collectFormData() {
            return {
                id: document.getElementById('form-id')?.value,
                title: document.getElementById('form-title').value.trim(),
                description: document.getElementById('form-description').value.trim(),
                fields: this.getFormFields(),
                theme: document.getElementById('form-theme').value
            };
        },

        validateForm(data) {
            if (!data.title) {
                this.showError('Form title is required');
                return false;
            }

            if (!data.fields || data.fields.length === 0) {
                this.showError('At least one form field is required');
                return false;
            }

            return true;
        },

        getFormFields() {
            const fields = [];
            const fieldElements = document.querySelectorAll('.form-field');
            
            fieldElements.forEach(element => {
                const field = {
                    id: element.dataset.fieldId,
                    label: element.dataset.label,
                    type: element.dataset.type,
                    required: element.dataset.required === 'true'
                };

                if (['select', 'radio', 'checkbox'].includes(field.type)) {
                    field.options = JSON.parse(element.dataset.options || '[]');
                }

                fields.push(field);
            });

            return fields;
        },

        populateForm(data) {
            document.getElementById('form-title').value = data.title || '';
            document.getElementById('form-description').value = data.description || '';
            if (data.theme) {
                document.getElementById('form-theme').value = data.theme;
            }
            if (data.fields) {
                this.populateFormFields(data.fields);
            }
        },

        populateFormFields(fields) {
            const fieldsContainer = document.getElementById('form-fields');
            fieldsContainer.innerHTML = ''; // Clear existing fields
            
            fields.forEach(field => {
                const fieldElement = this.createFieldElement(field);
                fieldsContainer.appendChild(fieldElement);
            });
        },

        createFieldElement(field) {
            const div = document.createElement('div');
            div.className = 'form-field mb-3 p-3 border rounded position-relative';
            div.dataset.fieldId = field.id;
            div.dataset.label = field.label;
            div.dataset.type = field.type;
            div.dataset.required = field.required;
            if (field.options) {
                div.dataset.options = JSON.stringify(field.options);
            }

            // Add field content
            div.innerHTML = `
                <div class="field-actions position-absolute top-0 end-0 m-2">
                    <button type="button" class="btn btn-sm btn-outline-danger delete-field">×</button>
                </div>
                <h5>${field.label} ${field.required ? '<span class="text-danger">*</span>' : ''}</h5>
                <p class="mb-1 text-muted">Type: ${field.type}</p>
                ${this.renderFieldPreview(field)}
            `;

            // Add delete handler
            div.querySelector('.delete-field').addEventListener('click', () => {
                div.remove();
            });

            // Add speech recognition to preview inputs
            const inputs = div.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], textarea');
            inputs.forEach(input => this.addSpeechInput(input));

            return div;
        },

        renderFieldPreview(field) {
            switch (field.type) {
                case 'text':
                case 'email':
                case 'tel':
                case 'number':
                    return `<input type="${field.type}" class="form-control" placeholder="${field.label}" disabled>`;
                case 'textarea':
                    return `<textarea class="form-control" placeholder="${field.label}" disabled></textarea>`;
                case 'select':
                    return `
                        <select class="form-control" disabled>
                            ${field.options?.map(opt => `<option>${opt}</option>`).join('')}
                        </select>
                    `;
                case 'radio':
                    return `
                        <div>
                            ${field.options?.map(opt => `
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" disabled>
                                    <label class="form-check-label">${opt}</label>
                                </div>
                            `).join('')}
                        </div>
                    `;
                case 'checkbox':
                    return `
                        <div>
                            ${field.options?.map(opt => `
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" disabled>
                                    <label class="form-check-label">${opt}</label>
                                </div>
                            `).join('')}
                        </div>
                    `;
                default:
                    return '';
            }
        },

        showFieldModal() {
            const modal = new bootstrap.Modal(document.getElementById('field-modal'));
            modal.show();
        },

        addOptionInput() {
            const optionsContainer = document.getElementById('field-options');
            const optionDiv = document.createElement('div');
            optionDiv.className = 'input-group mb-2';
            
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'form-control';
            input.placeholder = 'Option text';
            
            const deleteButton = document.createElement('button');
            deleteButton.className = 'btn btn-outline-danger';
            deleteButton.type = 'button';
            deleteButton.innerHTML = '×';
            deleteButton.onclick = () => optionDiv.remove();
            
            optionDiv.appendChild(input);
            optionDiv.appendChild(deleteButton);
            optionsContainer.appendChild(optionDiv);
            
            // Add speech recognition to the new option input
            this.addSpeechInput(input);
        },

        saveField() {
            const label = document.getElementById('field-label').value.trim();
            const type = document.getElementById('field-type').value;
            const required = document.getElementById('field-required').checked;
            
            if (!label) {
                this.showError('Field label is required');
                return;
            }

            const field = {
                id: 'field_' + Date.now(),
                label,
                type,
                required
            };

            if (['select', 'radio', 'checkbox'].includes(type)) {
                const options = Array.from(document.querySelectorAll('#field-options input'))
                    .map(input => input.value.trim())
                    .filter(value => value);
                
                if (options.length === 0) {
                    this.showError('At least one option is required for this field type');
                    return;
                }
                
                field.options = options;
            }

            const fieldElement = this.createFieldElement(field);
            document.getElementById('form-fields').appendChild(fieldElement);

            // Reset and close modal
            document.getElementById('field-label').value = '';
            document.getElementById('field-required').checked = false;
            document.getElementById('field-options').innerHTML = '';
            bootstrap.Modal.getInstance(document.getElementById('field-modal')).hide();
        },

        showError(message) {
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger';
            alert.textContent = message;
            this.showAlert(alert);
        },

        showSuccess(message) {
            const alert = document.createElement('div');
            alert.className = 'alert alert-success';
            alert.textContent = message;
            this.showAlert(alert);
        },

        showAlert(alertElement) {
            const alertsContainer = document.getElementById('alerts-container');
            if (alertsContainer) {
                alertsContainer.innerHTML = '';
                alertsContainer.appendChild(alertElement);
                setTimeout(() => {
                    alertElement.remove();
                }, 5000);
            }
        },

        showLoading(message) {
            const loader = document.getElementById('loader');
            if (loader) {
                loader.textContent = message;
                loader.style.display = 'block';
            }
        },

        hideLoading() {
            const loader = document.getElementById('loader');
            if (loader) {
                loader.style.display = 'none';
            }
        },

        // Add speech recognition setup
        setupSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window)) {
                console.warn('Speech recognition not supported');
                return;
            }

            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';

            this.recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                if (this.currentSpeechInput) {
                    this.currentSpeechInput.value = text;
                    this.currentSpeechInput.dispatchEvent(new Event('change'));
                }
            };

            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.showError('Speech recognition failed. Please try again.');
            };

            this.recognition.onend = () => {
                const micButton = this.currentSpeechInput?.parentElement.querySelector('.mic-button');
                if (micButton) {
                    micButton.classList.remove('listening');
                }
                this.currentSpeechInput = null;
            };
        },

        // Add speech input to any input field
        addSpeechInput(input) {
            if (!('webkitSpeechRecognition' in window)) return;

            const wrapper = document.createElement('div');
            wrapper.className = 'input-group';
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);

            const micButton = document.createElement('button');
            micButton.type = 'button';
            micButton.className = 'btn btn-outline-secondary mic-button';
            micButton.innerHTML = '<i class="fas fa-microphone"></i>';
            wrapper.appendChild(micButton);

            micButton.addEventListener('click', () => {
                if (this.currentSpeechInput) {
                    this.recognition.stop();
                }
                this.currentSpeechInput = input;
                micButton.classList.add('listening');
                this.recognition.start();
            });
        }
    };

    formBuilder.init();
}); 