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

                {{-- Verification Card --}}
                <div class="card border-0 shadow-lg rounded-4" style="backdrop-filter: blur(10px); background: rgba(255,255,255,0.95);">
                    <div class="card-body p-4 p-md-5">

                        {{-- Icon --}}
                        <div class="text-center mb-4">
                            <div class="d-inline-flex align-items-center justify-content-center bg-light rounded-3 mb-3" style="width: 56px; height: 56px;">
                                <i class="fa-solid fa-envelope-circle-check fa-xl text-primary"></i>
                            </div>
                            <h4 class="fw-bold text-dark mb-2">Verify Your Identity</h4>
                            <p class="text-muted mb-0 small">
                                We sent a 6-digit code to<br>
                                <span class="fw-medium text-dark">{{ $maskedEmail }}</span>
                            </p>
                        </div>

                        {{-- OTP Form --}}
                        <form wire:submit="verifyTwoFactor"
                            x-data="{
                                digits: ['', '', '', '', '', ''],
                                updateToken() {
                                    $wire.token = this.digits.join('');
                                },
                                handleInput(index, event) {
                                    const value = event.target.value;
                                    if (value.length === 1 && /^[0-9]$/.test(value)) {
                                        this.digits[index] = value;
                                        this.updateToken();
                                        if (index < 5) {
                                            const inputs = event.target.closest('.otp-inputs').querySelectorAll('input');
                                            inputs[index + 1].focus();
                                        }
                                    } else if (value.length === 0) {
                                        this.digits[index] = '';
                                        this.updateToken();
                                    } else {
                                        event.target.value = this.digits[index] || '';
                                    }
                                },
                                handleKeydown(index, event) {
                                    if (event.key === 'Backspace' && !this.digits[index] && index > 0) {
                                        event.preventDefault();
                                        const inputs = event.target.closest('.otp-inputs').querySelectorAll('input');
                                        inputs[index - 1].focus();
                                    }
                                },
                                handlePaste(event) {
                                    event.preventDefault();
                                    const pasteData = event.clipboardData.getData('text').trim();
                                    if (/^\d{6}$/.test(pasteData)) {
                                        pasteData.split('').forEach((digit, i) => {
                                            this.digits[i] = digit;
                                        });
                                        this.updateToken();
                                        const inputs = event.target.closest('.otp-inputs').querySelectorAll('input');
                                        inputs[5].focus();
                                    }
                                }
                            }"
                            @paste="handlePaste($event)">

                            {{-- OTP Input Fields --}}
                            <div class="otp-inputs d-flex justify-content-center gap-2 mb-3">
                                <template x-for="(digit, index) in digits" :key="index">
                                    <input
                                        type="text"
                                        class="form-control text-center fw-bold fs-4 border-2 rounded-3"
                                        style="width: 48px; height: 56px;"
                                        maxlength="1"
                                        x-model="digits[index]"
                                        @input="handleInput(index, $event)"
                                        @keydown="handleKeydown(index, $event)"
                                        inputmode="numeric"
                                        pattern="[0-9]"
                                        autocomplete="one-time-code"
                                    >
                                </template>
                            </div>

                            {{-- Error Message --}}
                            @error('token')
                                <div class="alert alert-danger py-2 text-center small mb-3">
                                    <i class="fa-solid fa-circle-exclamation me-1"></i>
                                    {{ $message }}
                                </div>
                            @enderror

                            {{-- Trust Device Checkbox --}}
                            <div class="mb-4">
                                <div class="form-check d-flex align-items-center justify-content-center gap-2">
                                    <input
                                        type="checkbox"
                                        class="form-check-input"
                                        id="rememberDevice"
                                        wire:model="remember_device"
                                    >
                                    <label class="form-check-label text-muted small" for="rememberDevice">
                                        <i class="fa-solid fa-shield-halved me-1"></i>
                                        Trust this device for 30 days
                                    </label>
                                </div>
                            </div>

                            {{-- Verify Button --}}
                            <div class="d-grid mb-3">
                                <button
                                    type="submit"
                                    class="btn btn-dark btn-lg fw-semibold py-3 rounded-3"
                                    wire:loading.attr="disabled"
                                >
                                    <span wire:loading.remove wire:target="verifyTwoFactor">
                                        Verify Code
                                    </span>
                                    <span wire:loading wire:target="verifyTwoFactor">
                                        <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                                        Verifying...
                                    </span>
                                </button>
                            </div>

                            {{-- Resend Code --}}
                            <div class="text-center">
                                <p class="text-muted small mb-2">Didn't receive the code?</p>
                                <button
                                    type="button"
                                    wire:click="resendCode"
                                    class="btn btn-link text-primary fw-medium p-0 text-decoration-none"
                                    wire:loading.attr="disabled"
                                >
                                    <span wire:loading.remove wire:target="resendCode">
                                        <i class="fa-solid fa-rotate-right me-1"></i>
                                        Resend Code
                                    </span>
                                    <span wire:loading wire:target="resendCode">
                                        <span class="spinner-border spinner-border-sm me-1" role="status"></span>
                                        Sending...
                                    </span>
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                {{-- Back to Login Link --}}
                <div class="text-center mt-4">
                    <a href="{{ route('login') }}" class="text-dark text-decoration-none fw-medium">
                        <i class="fa-solid fa-arrow-left me-2"></i>
                        Back to Login
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
