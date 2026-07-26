<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class PermissionCategory extends Model
{
    use HasFactory, HasUuids, SoftDeletes;

    /**
     * Indicates the IDs are non-incrementing (UUID).
     */
    public $incrementing = false;

    /**
     * The primary key type is a string (UUID).
     */
    protected $keyType = 'string';

    /**
     * All attributes are mass assignable.
     */
    protected $guarded = [];

    /**
     * A permission category can have many permissions.
     */
    public function permissions(): HasMany
    {
        return $this->hasMany(Permission::class, 'category_id');
    }
}
