<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class TrustedDevice extends Model
{
    use HasUuids;

    public $incrementing = false;

    protected $keyType = 'string';

    protected $fillable = [
        'user_id',
        'device_fingerprint',
        'device_name',
        'ip_address',
        'user_agent',
        'trusted_at',
        'expires_at',
        'last_used_at',
        'is_active',
    ];

    protected function casts(): array
    {
        return [
            'trusted_at' => 'datetime',
            'expires_at' => 'datetime',
            'last_used_at' => 'datetime',
            'is_active' => 'boolean',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function isExpired(): bool
    {
        return $this->expires_at && now()->isAfter($this->expires_at);
    }

    public function isValid(): bool
    {
        return $this->is_active && ! $this->isExpired();
    }

    public function updateLastUsed(): void
    {
        $this->update(['last_used_at' => now()]);
    }

    public function deactivate(): void
    {
        $this->update(['is_active' => false]);
    }

    public static function createForUser(
        string $userId,
        string $deviceFingerprint,
        string $deviceName,
        string $ipAddress,
        string $userAgent,
        int $trustDays = 30
    ): self {
        return self::create([
            'user_id' => $userId,
            'device_fingerprint' => $deviceFingerprint,
            'device_name' => $deviceName,
            'ip_address' => $ipAddress,
            'user_agent' => $userAgent,
            'trusted_at' => now(),
            'expires_at' => now()->addDays($trustDays),
            'last_used_at' => now(),
            'is_active' => true,
        ]);
    }

    public static function findValidDevice(string $userId, string $deviceFingerprint): ?self
    {
        return self::where('user_id', $userId)
            ->where('device_fingerprint', $deviceFingerprint)
            ->where('is_active', true)
            ->where(function ($query) {
                $query->whereNull('expires_at')
                    ->orWhere('expires_at', '>', now());
            })
            ->first();
    }
}
