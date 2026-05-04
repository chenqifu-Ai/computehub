package com.chargecloud;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.chargecloud.mapper")
public class ChargecloudApplication {
    public static void main(String[] args) {
        SpringApplication.run(ChargecloudApplication.class, args);
    }
}