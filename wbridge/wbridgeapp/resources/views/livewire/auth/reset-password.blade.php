<div>
    <section>
        <div class="container">
            <div class="row mb-8">
                <div class="col-xl-4 offset-xl-4 col-md-12 col-12">
                    <div class="text-center">
                        <a class='fs-2 fw-bold d-flex align-items-center gap-2 justify-content-center mb-6' href='{{ route('login') }}'>
                            <img src="{{ asset('images/brand/logo/logo-icon.svg') }}" alt="" />
                            <span>Dasher</span>
                        </a>
                        @if ($showTokenForm)
                            <h1 class="mb-1">Reset Code Verification</h1>
                            <p class="mb-0">
                                We sent a code to
                                <a href="#" class="text-inherit">{{ $email }}</a>
                            </p>
                        @else
                            <h1 class="mb-1">Set New Password</h1>
                            <p>Enter your new password</p>
                        @endif
                    </div>
                </div>
            </div>
            <div class="row justify-content-center">
                <div class="col-xl-6 col-lg-8 col-md-10 col-12">
                    <div class="card card-lg mb-6">
                        <div class="card-body p-6">
                            @if ($showTokenForm)
                                <form wire:submit="resetPassword"
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
                                                    const inputs = event.target.parentElement.querySelectorAll('input');
                                                    inputs[index + 1].focus();
                                                }
                                            } else if (value.length === 0) {
                                                this.digits[index] = '';
                                                this.updateToken();
                                            } else {
                                                event.target.value = '';
                                            }
                                        },
                                        handleKeydown(index, event) {
                                            if (event.key === 'Backspace' && !this.digits[index] && index > 0) {
                                                event.preventDefault();
                                                const inputs = event.target.parentElement.querySelectorAll('input');
                                                inputs[index - 1].focus();
                                            }
                                        },
                                        handlePaste(event) {
                                            event.preventDefault();
                                            const pasteData = event.clipboardData.getData('text').trim();
                                            if (/^\d{6}$/.test(pasteData)) {
                                                const pasteDigits = pasteData.split('');
                                                pasteDigits.forEach((digit, i) => {
                                                    this.digits[i] = digit;
                                                });
                                                this.updateToken();
                                                const inputs = event.target.parentElement.querySelectorAll('input');
                                                inputs[5].focus();
                                            }
                                        }
                                    }"
                                    @paste="handlePaste($event)">
                                    <div class="d-flex flex-row gap-2 mb-3">
                                        <template x-for="(digit, index) in digits" :key="index">
                                            <input
                                                type="text"
                                                class="form-control inputpass-code"
                                                maxlength="1"
                                                x-model="digits[index]"
                                                @input="handleInput(index, $event)"
                                                @keydown="handleKeydown(index, $event)"
                                                inputmode="numeric"
                                                pattern="[0-9]"
                                            >
                                        </template>
                                    </div>

                                    @error('token')
                                        <div class="text-danger text-center mb-3">
                                            <small>{{ $message }}</small>
                                        </div>
                                    @enderror

                                    <x-forms.button
                                        type="submit"
                                        :block="true"
                                        loadingText="Verifying..."
                                        loadingTarget="resetPassword"
                                        class="mb-3"
                                    >
                                        Verify Code
                                    </x-forms.button>

                                    <div class="text-center mt-4">
                                        <a href="{{ route('forgot-password') }}">Request New Code</a>
                                        <span class="mx-2">|</span>
                                        <a href="{{ route('login') }}">Back to Login</a>
                                    </div>
                                </form>
                            @else
                                <form wire:submit="resetPassword">
                                    <x-forms.input
                                        wire:model="password"
                                        type="password"
                                        name="password"
                                        label="New Password"
                                        placeholder="Enter new password"
                                        :wrapper="false"
                                        required
                                    />

                                    <x-forms.input
                                        wire:model="password_confirmation"
                                        type="password"
                                        name="password_confirmation"
                                        label="Confirm Password"
                                        placeholder="Confirm new password"
                                        :wrapper="false"
                                        required
                                    />

                                    <x-forms.button
                                        type="submit"
                                        :block="true"
                                        loadingText="Resetting Password..."
                                        loadingTarget="resetPassword"
                                        class="mb-3"
                                    >
                                        Reset Password
                                    </x-forms.button>

                                    <div class="text-center mt-4">
                                        <a href="{{ route('login') }}">Back to Login</a>
                                    </div>
                                </form>
                            @endif
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
</div>
