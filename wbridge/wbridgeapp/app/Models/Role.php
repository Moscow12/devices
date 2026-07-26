<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\SoftDeletes;
use Spatie\Permission\Models\Role as SpatieRole;

class Role extends SpatieRole
{
    use HasUuids, SoftDeletes;

    /**
     * The primary key for the model.
     *
     * @var string
     */
    protected $primaryKey = 'id';

    /**
     * Indicates that the IDs are non-incrementing (UUID).
     *
     * @var bool
     */
    public $incrementing = false;

    /**
     * The primary key type is a string (UUID).
     *
     * @var string
     */
    protected $keyType = 'string';

    //    /**
    //     * Boot the model and automatically generate a UUID for the primary key.
    //     */
    //    protected static function boot(): void
    //    {
    //        parent::boot();
    //
    //        static::creating(function (self $model): void {
    //            if (empty($model->{$model->getKeyName()})) {
    //                $model->{$model->getKeyName()} = (string) Str::uuid();
    //            }
    //        });
    //    }
}
