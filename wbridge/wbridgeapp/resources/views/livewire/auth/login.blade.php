<div class="min-vh-100 d-flex align-items-center justify-content-center position-relative overflow-hidden"
     style="background: linear-gradient(180deg, #87CEEB 0%, #B0E0E6 30%, #E0F4FF 60%, #FFFFFF 100%);">

    {{-- Decorative Cloud Elements --}}
    <div class="position-absolute w-100 h-100" style="pointer-events: none; overflow: hidden;">
        {{-- Large arc decoration --}}
        <div class="position-absolute" style="
            width: 800px;
            height: 800px;
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        "></div>
        <div class="position-absolute" style="
            width: 600px;
            height: 600px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 50%;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        "></div>

        {{-- Cloud shapes at bottom --}}
        <div class="position-absolute" style="
            bottom: -50px;
            left: -100px;
            width: 300px;
            height: 150px;
            background: rgba(255,255,255,0.6);
            border-radius: 100px;
            filter: blur(30px);
        "></div>
        <div class="position-absolute" style="
            bottom: -30px;
            right: -50px;
            width: 250px;
            height: 120px;
            background: rgba(255,255,255,0.5);
            border-radius: 100px;
            filter: blur(25px);
        "></div>
        <div class="position-absolute" style="
            bottom: 0;
            left: 30%;
            width: 400px;
            height: 100px;
            background: rgba(255,255,255,0.4);
            border-radius: 100px;
            filter: blur(20px);
        "></div>
    </div>

    {{-- Logo in top left --}}
    <div class="position-absolute top-0 start-0 p-4">
        @if($workstation && $workstation->logo)
            <div class="d-flex align-items-center gap-2">
                <img
                    src="{{ asset('storage/' . $workstation->logo) }}"
                    alt="{{ $workstation->workstation_name ?? $appName }}"
                    style="max-height: 40px; object-fit: contain;"
                />
                <span class="fw-semibold text-dark">{{ $workstation->workstation_name ?? $appName }}</span>
            </div>
        @else
            <div class="d-flex align-items-center gap-2">
                <div class="d-inline-flex align-items-center justify-content-center bg-dark rounded-2" style="width: 32px; height: 32px;">
                    <span class="text-white fw-bold small">{{ substr($appName, 0, 1) }}</span>
                </div>
                <span class="fw-semibold text-dark">{{ $appName }}</span>
            </div>
        @endif
    </div>

    {{-- Main Content --}}
    <div class="container position-relative" style="z-index: 10;">
        <div class="row justify-content-center">
            <div class="col-xl-4 col-lg-5 col-md-7 col-sm-9">

                {{-- Login Card --}}
                <div class="card border-0 shadow-lg rounded-4" style="backdrop-filter: blur(10px); background: rgba(255,255,255,0.95);">
                    <div class="card-body p-4 p-md-5">

                        {{-- Icon & Title --}}
                        <div class="text-center mb-4">
                            <div class="d-inline-flex align-items-center justify-content-center bg-light rounded-3 mb-3" style="width: 56px; height: 56px;">
                                <i class="fa-solid fa-right-to-bracket fa-xl text-dark"></i>
                            </div>
                            <h4 class="fw-bold text-dark mb-2">Sign in to your account</h4>
                            <p class="text-muted mb-0 small">
                                Enter your credentials to access<br>your dashboard
                            </p>
                        </div>

                        {{-- Login Form --}}
                        <form wire:submit="loginUser">
                            {{-- Login Field --}}
                            <div class="mb-3">
                                <div class="input-group">
                                    <span class="input-group-text bg-light border-end-0">
                                        <i class="fa-solid fa-envelope text-muted"></i>
                                    </span>
                                    <input
                                        type="text"
                                        id="login"
                                        wire:model="login"
                                        class="form-control border-start-0 ps-0 @error('login') is-invalid @enderror"
                                        placeholder="Email, Username or Phone"
                                        autocomplete="username"
                                    />
                                </div>
                                @error('login')
                                    <div class="text-danger small mt-1">{{ $message }}</div>
                                @enderror
                            </div>

                            {{-- Password Field --}}
                            <div class="mb-3">
                                <div class="input-group">
                                    <span class="input-group-text bg-light border-end-0">
                                        <i class="fa-solid fa-lock text-muted"></i>
                                    </span>
                                    <input
                                        type="password"
                                        id="password"
                                        wire:model="password"
                                        class="form-control border-start-0 ps-0 @error('password') is-invalid @enderror"
                                        placeholder="Password"
                                        autocomplete="current-password"
                                    />
                                </div>
                                @error('password')
                                    <div class="text-danger small mt-1">{{ $message }}</div>
                                @enderror
                            </div>

                            {{-- Forgot Password --}}
                            <div class="text-end mb-4">
                                <a href="{{ route('forgot-password') }}" class="text-primary text-decoration-none small fw-medium">
                                    Forgot password?
                                </a>
                            </div>

                            {{-- Submit Button --}}
                            <div class="d-grid mb-3">
                                <button
                                    type="submit"
                                    class="btn btn-dark btn-lg fw-semibold py-3 rounded-3"
                                    wire:loading.attr="disabled"
                                >
                                    <span wire:loading.remove wire:target="loginUser">
                                        Get Started
                                    </span>
                                    <span wire:loading wire:target="loginUser">
                                        <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                                        Signing In...
                                    </span>
                                </button>
                            </div>
                        </form>

                        @if($twoFactorEnabled)
                            {{-- Divider --}}
                            <div class="d-flex align-items-center my-4">
                                <hr class="flex-grow-1 text-muted">
                                <span class="px-3 text-muted small">Or sign in with</span>
                                <hr class="flex-grow-1 text-muted">
                            </div>

                            {{-- Social Login Buttons --}}
                            <div class="d-flex justify-content-center gap-3">
                                <a href="#" class="btn btn-outline-secondary rounded-3 px-4 py-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
                                        <path d="M15.545 6.558a9.42 9.42 0 0 1 .139 1.626c0 2.434-.87 4.492-2.384 5.885h.002C11.978 15.292 10.158 16 8 16A8 8 0 1 1 8 0a7.689 7.689 0 0 1 5.352 2.082l-2.284 2.284A4.347 4.347 0 0 0 8 3.166c-2.087 0-3.86 1.408-4.492 3.304a4.792 4.792 0 0 0 0 3.063h.003c.635 1.893 2.405 3.301 4.492 3.301 1.078 0 2.004-.276 2.722-.764h-.003a3.702 3.702 0 0 0 1.599-2.431H8v-3.08h7.545z"/>
                                    </svg>
                                </a>
                                <a href="#" class="btn btn-outline-secondary rounded-3 px-4 py-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="#1877F2" viewBox="0 0 16 16">
                                        <path d="M16 8.049c0-4.446-3.582-8.05-8-8.05C3.58 0-.002 3.603-.002 8.05c0 4.017 2.926 7.347 6.75 7.951v-5.625h-2.03V8.05H6.75V6.275c0-2.017 1.195-3.131 3.022-3.131.876 0 1.791.157 1.791.157v1.98h-1.009c-.993 0-1.303.621-1.303 1.258v1.51h2.218l-.354 2.326H9.25V16c3.824-.604 6.75-3.934 6.75-7.951z"/>
                                    </svg>
                                </a>
                                <a href="#" class="btn btn-outline-secondary rounded-3 px-4 py-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
                                        <path d="M11.182.008C11.148-.03 9.923.023 8.857 1.18c-1.066 1.156-.902 2.482-.878 2.516.024.034 1.52.087 2.475-1.258.955-1.345.762-2.391.728-2.43Zm3.314 11.733c-.048-.096-2.325-1.234-2.113-3.422.212-2.189 1.675-2.789 1.698-2.854.023-.065-.597-.79-1.254-1.157a3.692 3.692 0 0 0-1.563-.434c-.108-.003-.483-.095-1.254.116-.508.139-1.653.589-1.968.607-.316.018-1.256-.522-2.267-.665-.647-.125-1.333.131-1.824.328-.49.196-1.422.754-2.074 2.237-.652 1.482-.311 3.83-.067 4.56.244.729.625 1.924 1.273 2.796.576.984 1.34 1.667 1.659 1.899.319.232 1.219.386 1.843.067.502-.308 1.408-.485 1.766-.472.357.013 1.061.154 1.782.539.571.197 1.111.115 1.652-.105.541-.221 1.324-1.059 2.238-2.758.347-.79.505-1.217.473-1.282Z"/>
                                    </svg>
                                </a>
                            </div>
                        @endif
                    </div>
                </div>

                {{-- Security Notice --}}
                <div class="text-center mt-4">
                    <p class="text-dark small mb-0">
                        <i class="fa-solid fa-shield-halved me-1"></i>
                        Your connection is secure and encrypted
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
