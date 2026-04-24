package com.chargecloud.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.chargecloud.common.Result;
import com.chargecloud.entity.Station;
import com.chargecloud.service.StationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/stations")
public class StationController {

    @Autowired
    private StationService stationService;

    @GetMapping
    public Result<Page<Station>> list(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size,
            @RequestParam(required = false) String city,
            @RequestParam(required = false) Integer status) {
        Page<Station> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<Station> wrapper = new LambdaQueryWrapper<>();
        if (city != null) wrapper.eq(Station::getCity, city);
        if (status != null) wrapper.eq(Station::getStatus, status);
        return Result.success(stationService.page(pageParam, wrapper));
    }

    @PostMapping
    public Result<Station> create(@RequestBody Station station) {
        station.setStatus(1);
        stationService.save(station);
        return Result.success(station);
    }

    @GetMapping("/{id}")
    public Result<Station> getById(@PathVariable Long id) {
        return Result.success(stationService.getById(id));
    }

    @PutMapping("/{id}")
    public Result<Station> update(@PathVariable Long id, @RequestBody Station station) {
        station.setId(id);
        stationService.updateById(station);
        return Result.success(station);
    }

    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        return Result.success(stationService.removeById(id));
    }
}