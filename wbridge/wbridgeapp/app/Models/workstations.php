<?php

namespace App\Models;

use Database\Factories\WorkstationsFactory;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class workstations extends Model
{
    use HasFactory, HasUuids;

    protected $table = 'workstations';

    protected static function newFactory(): WorkstationsFactory
    {
        return WorkstationsFactory::new();
    }
    protected $fillable = [
        'workstation_name',
        'location',
        'postal_code',
        'physical_address',
        'phone_number',
        'tin_number',
        'email_address',
        'logo',
        'official_stamp',
        'letter_head',
        'country_id',
        'region_id',
        'district_id',
        'ward_id',
        'added_by',
    ];
    public function added_by()
    {
        return $this->belongsTo(User::class, 'added_by');
    }

    public function ward()
    {
        return $this->belongsTo(wards::class, 'ward_id');
    }

    public function region()
    {
        return $this->belongsTo(regions::class, 'region_id');
    }
    public function district()
    {
        return $this->belongsTo(districts::class, 'district_id');
    }

    public function country()
    {
        return $this->belongsTo(countries::class, 'country_id');
    }

    public function employees()
    {
        return $this->hasMany(Employee::class, 'employee_id');
    }
}
