<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config('app.name', 'WBridge') }} - Dashboard</title>

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ route('dashboard') }}">
                <i class="fas fa-weight"></i> {{ config('app.name', 'WBridge') }}
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown">
                            <i class="fas fa-user-circle"></i> {{ auth()->user()->name ?? auth()->user()->username }}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="#"><i class="fas fa-user"></i> Profile</a></li>
                            <li><a class="dropdown-item" href="#"><i class="fas fa-cog"></i> Settings</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ route('logout') }}"><i class="fas fa-sign-out-alt"></i> Logout</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 col-lg-2">
                <div class="card">
                    <div class="card-header bg-dark text-white">
                        <i class="fas fa-bars"></i> Menu
                    </div>
                    <div class="list-group list-group-flush">
                        <a href="{{ route('dashboard') }}" class="list-group-item list-group-item-action active">
                            <i class="fas fa-tachometer-alt"></i> Dashboard
                        </a>

                        @can('view-weighbridge')
                        <a href="#" class="list-group-item list-group-item-action">
                            <i class="fas fa-weight"></i> Weighbridge
                        </a>
                        @endcan

                        @can('view-transactions')
                        <a href="#" class="list-group-item list-group-item-action">
                            <i class="fas fa-exchange-alt"></i> Transactions
                        </a>
                        @endcan

                        @can('view-vehicles')
                        <a href="#" class="list-group-item list-group-item-action">
                            <i class="fas fa-truck"></i> Vehicles
                        </a>
                        @endcan

                        @can('view-reports')
                        <a href="#" class="list-group-item list-group-item-action">
                            <i class="fas fa-chart-bar"></i> Reports
                        </a>
                        @endcan

                        @can('view-users')
                        <a href="#" class="list-group-item list-group-item-action">
                            <i class="fas fa-users"></i> Users
                        </a>
                        @endcan

                        @can('view-settings')
                        <a href="#" class="list-group-item list-group-item-action">
                            <i class="fas fa-cog"></i> Settings
                        </a>
                        @endcan
                    </div>
                </div>
            </div>

            <!-- Main Content -->
            <div class="col-md-9 col-lg-10">
                <!-- Welcome Card -->
                <div class="card mb-4">
                    <div class="card-body">
                        <h2 class="card-title">
                            <i class="fas fa-home"></i> Welcome, {{ auth()->user()->name ?? auth()->user()->username }}!
                        </h2>
                        <p class="card-text text-muted">
                            Role:
                            @if(auth()->user()->isSuperAdmin())
                                <span class="badge bg-danger">Super Administrator</span>
                            @else
                                @foreach(auth()->user()->roles as $role)
                                    <span class="badge bg-primary">{{ ucfirst($role->name) }}</span>
                                @endforeach
                            @endif
                        </p>
                    </div>
                </div>

                <!-- Stats Cards -->
                <div class="row">
                    @can('view-weighbridge')
                    <div class="col-md-6 col-lg-3 mb-4">
                        <div class="card text-white bg-primary">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="card-title text-uppercase mb-0">Today's Weight</h6>
                                        <h2 class="mt-2 mb-0">0</h2>
                                        <small>Transactions</small>
                                    </div>
                                    <div>
                                        <i class="fas fa-weight fa-3x opacity-50"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    @endcan

                    @can('view-transactions')
                    <div class="col-md-6 col-lg-3 mb-4">
                        <div class="card text-white bg-success">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="card-title text-uppercase mb-0">Total</h6>
                                        <h2 class="mt-2 mb-0">0</h2>
                                        <small>Transactions</small>
                                    </div>
                                    <div>
                                        <i class="fas fa-exchange-alt fa-3x opacity-50"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    @endcan

                    @can('view-vehicles')
                    <div class="col-md-6 col-lg-3 mb-4">
                        <div class="card text-white bg-warning">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="card-title text-uppercase mb-0">Vehicles</h6>
                                        <h2 class="mt-2 mb-0">0</h2>
                                        <small>Registered</small>
                                    </div>
                                    <div>
                                        <i class="fas fa-truck fa-3x opacity-50"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    @endcan

                    @can('view-users')
                    <div class="col-md-6 col-lg-3 mb-4">
                        <div class="card text-white bg-info">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="card-title text-uppercase mb-0">Users</h6>
                                        <h2 class="mt-2 mb-0">{{ \App\Models\User::count() }}</h2>
                                        <small>Active</small>
                                    </div>
                                    <div>
                                        <i class="fas fa-users fa-3x opacity-50"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    @endcan
                </div>

                <!-- Quick Actions -->
                <div class="card">
                    <div class="card-header bg-dark text-white">
                        <i class="fas fa-bolt"></i> Quick Actions
                    </div>
                    <div class="card-body">
                        <div class="row">
                            @can('create-transactions')
                            <div class="col-md-4 mb-3">
                                <a href="#" class="btn btn-primary btn-lg w-100">
                                    <i class="fas fa-plus-circle"></i> New Transaction
                                </a>
                            </div>
                            @endcan

                            @can('view-reports')
                            <div class="col-md-4 mb-3">
                                <a href="#" class="btn btn-success btn-lg w-100">
                                    <i class="fas fa-file-alt"></i> View Reports
                                </a>
                            </div>
                            @endcan

                            @can('create-vehicles')
                            <div class="col-md-4 mb-3">
                                <a href="#" class="btn btn-warning btn-lg w-100">
                                    <i class="fas fa-truck"></i> Register Vehicle
                                </a>
                            </div>
                            @endcan
                        </div>
                    </div>
                </div>

                <!-- Your Permissions (for testing) -->
                @if(config('app.debug'))
                <div class="card mt-4">
                    <div class="card-header bg-secondary text-white">
                        <i class="fas fa-shield-alt"></i> Your Permissions (Debug Mode)
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-12">
                                <strong>Roles:</strong>
                                @foreach(auth()->user()->roles as $role)
                                    <span class="badge bg-primary">{{ $role->name }}</span>
                                @endforeach

                                @if(auth()->user()->isSuperAdmin())
                                    <span class="badge bg-danger">Super Admin (All Permissions)</span>
                                @endif
                            </div>
                            <div class="col-md-12 mt-3">
                                <strong>Direct Permissions:</strong>
                                @forelse(auth()->user()->permissions as $permission)
                                    <span class="badge bg-info">{{ $permission->name }}</span>
                                @empty
                                    <span class="text-muted">None (inherited from role)</span>
                                @endforelse
                            </div>
                        </div>
                    </div>
                </div>
                @endif
            </div>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
