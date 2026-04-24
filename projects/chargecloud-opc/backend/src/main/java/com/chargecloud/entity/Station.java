package com.chargecloud.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("charging_station")
public class Station {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String name;
    private Long operatorId;
    private String province;
    private String city;
    private String district;
    private String address;
    private BigDecimal longitude;
    private BigDecimal latitude;
    private Integer totalPiles;
    private Integer availablePiles;
    private BigDecimal parkingFee;
    private Integer status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}