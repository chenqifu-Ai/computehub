package com.chargecloud.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.chargecloud.common.Result;
import com.chargecloud.entity.Pile;
import com.chargecloud.service.PileService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/piles")
public class PileController {

    @Autowired
    private PileService pileService;

    @GetMapping
    public Result<Page<Pile>> list(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size,
            @RequestParam(required = false) Long stationId,
            @RequestParam(required = false) Integer status) {
        Page<Pile> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<Pile> wrapper = new LambdaQueryWrapper<>();
        if (stationId != null) wrapper.eq(Pile::getStationId, stationId);
        if (status != null) wrapper.eq(Pile::getStatus, status);
        return Result.success(pileService.page(pageParam, wrapper));
    }

    @PostMapping
    public Result<Pile> create(@RequestBody Pile pile) {
        pile.setStatus(1);
        pileService.save(pile);
        return Result.success(pile);
    }

    @GetMapping("/{id}")
    public Result<Pile> getById(@PathVariable Long id) {
        return Result.success(pileService.getById(id));
    }

    @PutMapping("/{id}")
    public Result<Pile> update(@PathVariable Long id, @RequestBody Pile pile) {
        pile.setId(id);
        pileService.updateById(pile);
        return Result.success(pile);
    }

    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        return Result.success(pileService.removeById(id));
    }

    @GetMapping("/{id}/status")
    public Result<Pile> getStatus(@PathVariable Long id) {
        return Result.success(pileService.getById(id));
    }
}