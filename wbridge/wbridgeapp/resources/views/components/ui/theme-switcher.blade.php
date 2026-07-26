@props([
    'iconLibrary' => 'bi', // 'bi' for Bootstrap Icons, 'ti' for Tabler Icons
    'buttonClass' => 'btn-light',
    'withWrapper' => false
])

@php
    $iconClasses = [
        'bi' => [
            'sun' => 'bi-sun-fill',
            'moon' => 'bi-moon-stars',
            'auto' => 'bi-circle-half'
        ],
        'ti' => [
            'sun' => 'ti-sun',
            'moon' => 'ti-moon-stars',
            'auto' => 'ti-circle-half-2'
        ]
    ];

    $icons = $iconClasses[$iconLibrary];
    $baseIconClass = $iconLibrary === 'bi' ? 'bi' : 'ti';
@endphp

@if($withWrapper)
<div class="position-absolute end-0 bottom-0 m-4">
@endif

<div class="dropdown">
    <button class="btn {{ $buttonClass }} btn-icon rounded-circle d-flex align-items-center"
            type="button"
            aria-expanded="false"
            data-bs-toggle="dropdown"
            data-theme-toggle
            aria-label="Toggle theme (auto)">
        <i class="{{ $baseIconClass }} theme-icon-active lh-1 {{ $iconLibrary === 'ti' ? 'fs-5' : '' }}">
            <i class="{{ $baseIconClass }} theme-icon {{ $icons['sun'] }}"></i>
        </i>
        <span class="visually-hidden bs-theme-text">Toggle theme</span>
    </button>
    <ul class="dropdown-menu dropdown-menu-end shadow">
        <li>
            <button type="button"
                    class="dropdown-item d-flex align-items-center active"
                    data-bs-theme-value="light"
                    aria-pressed="true">
                <i class="{{ $baseIconClass }} theme-icon {{ $baseIconClass }} {{ $icons['sun'] }}"></i>
                <span class="ms-2">Light</span>
            </button>
        </li>
        <li>
            <button type="button"
                    class="dropdown-item d-flex align-items-center"
                    data-bs-theme-value="dark"
                    aria-pressed="false">
                <i class="{{ $baseIconClass }} theme-icon {{ $icons['moon'] }}"></i>
                <span class="ms-2">Dark</span>
            </button>
        </li>
        <li>
            <button type="button"
                    class="dropdown-item d-flex align-items-center"
                    data-bs-theme-value="auto"
                    aria-pressed="false">
                <i class="{{ $baseIconClass }} theme-icon {{ $icons['auto'] }}"></i>
                <span class="ms-2">Auto</span>
            </button>
        </li>
    </ul>
</div>

@if($withWrapper)
</div>
@endif
