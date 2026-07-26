<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>{{ config('app.name', 'WBridge') }} - Authentication</title>

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

    <!-- Livewire Styles -->
    @livewireStyles
</head>

<body>
    <main class="d-flex flex-column justify-content-center min-vh-100">

        {{ $slot }}

    </main>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

    <!-- Livewire Scripts -->
    @livewireScripts

    <!-- Toast notifications (if needed) -->
    <script>
        window.addEventListener('toastMagic', event => {
            const toastElement = document.createElement('div');
            toastElement.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastElement.innerHTML = `
                <div class="toast show" role="alert">
                    <div class="toast-header bg-${event.detail.status || 'success'} text-white">
                        <strong class="me-auto">${event.detail.title || 'Notification'}</strong>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                    </div>
                    <div class="toast-body">
                        ${event.detail.message || ''}
                    </div>
                </div>
            `;
            document.body.appendChild(toastElement);
            setTimeout(() => toastElement.remove(), 5000);
        });
    </script>
</body>

</html>
