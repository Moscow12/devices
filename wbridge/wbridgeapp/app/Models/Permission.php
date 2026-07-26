<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\SoftDeletes;
use Spatie\Permission\Models\Permission as SpatiePermission;

class Permission extends SpatiePermission
{
    use HasFactory, HasUuids, SoftDeletes;

    /**
     * The primary key for the model.
     *
     * @var string
     */
    protected $primaryKey = 'id';

    /**
     * IDs are non-incrementing (UUID).
     */
    public $incrementing = false;

    /**
     * The primary key type is string (UUID).
     *
     * @var string
     */
    protected $keyType = 'string';

    /**
     * All attributes are mass assignable.
     *
     * @var array<int,string>
     */
    protected $guarded = [];

    /**
     * A permission belongs to a permission category.
     */

    public function category(): BelongsTo
    {
        return $this->belongsTo(PermissionCategory::class, 'category_id', 'id');
    }
}
