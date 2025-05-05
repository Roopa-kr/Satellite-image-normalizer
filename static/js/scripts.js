// Wait for the whole HTML document to load before running this script
document.addEventListener('DOMContentLoaded', () => {
    // Get references to key HTML elements
    const form = document.getElementById('upload-form');        // The form where users upload their ZIP
    const fileInput = document.getElementById('file');          // The actual file input element
    const fileNameDiv = document.getElementById('file-name');   // A div to show the selected file name
    const submitBtn = document.getElementById('submit-btn');    // The form's submit button
    const spinner = document.getElementById('loading-spinner'); // A loading spinner to show during processing

    // Check if the form and file input exist before continuing
    if (form && fileInput) {
        // When the user selects a file
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];  // Get the first (and only) file selected
                // Validate the file size (must be under 100MB)
                if (file.size > 100 * 1024 * 1024) {
                    alert('File size exceeds 100MB.');  // Warn the user
                    fileInput.value = '';               // Clear the selected file
                    return;                             // Stop further processing
                }
                // Show the file name to the user
                fileNameDiv.textContent = `Selected: ${file.name}`;
            } else {
                fileNameDiv.textContent = '';  // Clear filename display if no file is selected
            }
        });

        // When the form is submitted
        form.addEventListener('submit', () => {
            submitBtn.disabled = true;                    // Disable the submit button to prevent double clicks
            spinner.classList.remove('d-none');           // Show the loading spinner (assumes Bootstrap's d-none class is used to hide it by default)
        });
    }
});
