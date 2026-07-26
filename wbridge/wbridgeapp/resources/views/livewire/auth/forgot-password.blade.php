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
                        <h1 class="mb-1">Forgot your password?</h1>
                        <p>Enter your email below and we will send you a reset code</p>
                    </div>
                </div>
            </div>
            <div class="row justify-content-center">
                <div class="col-xl-5 col-lg-6 col-md-8 col-12">
                    <div class="card card-lg mb-6">
                        <div class="card-body p-6">
                            <form wire:submit="performPasswordReset" class="mb-6">
                                <x-forms.input
                                    wire:model="email"
                                    type="email"
                                    name="email"
                                    label="Email Address"
                                    placeholder="name@example.com"
                                    :wrapper="false"
                                    required
                                />

                                <x-forms.button
                                    type="submit"
                                    :block="true"
                                    loadingText="Sending Code..."
                                    loadingTarget="performPasswordReset"
                                >
                                    Send Reset Code
                                </x-forms.button>
                            </form>

                            <div class="text-center">
                                <a href="{{ route('login') }}">
                                    <span>Back to Login</span>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
</div>
