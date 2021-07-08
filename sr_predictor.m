function y = sr_predictor(feed_rate, wheel_speed, work_speed, power, Acc_n, Acc_t)

    load("D:\Kerry\python\randomforestmodel\rforestmodel.mat", 'mdl');
    Power_analysis = power;

    f1 = max(Power_analysis); %Max
    f2 = mean(Power_analysis); %Mean
    f3 = std(Power_analysis); %standard deviation
    f4 = skewness(Power_analysis); %Skewness
    f5 = kurtosis(Power_analysis); %Kurtosis
    f6 = max(Power_analysis) - min(Power_analysis); %Peak to peak value

    Acc_n_analysis = Acc_n; %Normal acceleration under analysis
    Acc_t_analysis = Acc_t; %Tangential acceleration under analysis

    f7 = max(Acc_n_analysis); %Max
    f8 = mean(abs(Acc_n_analysis)); %Mean
    f9 = skewness(Acc_n_analysis); %Skewness
    f10 = kurtosis(Acc_n_analysis); %Kurtosis

    f14 = max(Acc_t_analysis); %Max
    f15 = mean(abs(Acc_t_analysis)); %Mean
    f16 = skewness(Acc_t_analysis); %Skewness
    f17 = kurtosis(Acc_t_analysis); %Kurtosis

    N1 = length(Acc_n_analysis);
    N2 = length(Acc_t_analysis);
    samp = 10000; %Sampling frequency for acceleration signal
    r1 = ceil(N1 / 2);
    bin1 = [0:N1 - 1];
    freq1 = bin1 * samp / N1;
    r2 = ceil(N2 / 2);
    bin2 = [0:N2 - 1];
    freq2 = bin2 * samp / N2;
    An = fft(Acc_n_analysis, N1); %FFT
    Mag_N = abs(An);
    At = fft(Acc_t_analysis, N2); %FFT
    Mag_T = abs(At);

    f11 = sum(Mag_N.^2); %Total energy - normal acc
    f18 = sum(Mag_T.^2); %Total energy - tangential acc

    band_low1 = 1000; %Start of band-1
    band_high1 = 2000; %End of band-1

    band_low2 = 2750; %Start of band-2
    band_high2 = 3750; %End of band-2

    %Finding index where frequency and band are closest

    [~, index1] = min(abs(freq1 - band_low1));
    [~, index2] = min(abs(freq1 - band_high1));
    [~, index3] = min(abs(freq1 - band_low2));
    [~, index4] = min(abs(freq1 - band_high2));

    [~, index5] = min(abs(freq2 - band_low1));
    [~, index6] = min(abs(freq2 - band_high1));
    [~, index7] = min(abs(freq2 - band_low2));
    [~, index8] = min(abs(freq2 - band_high2));

    f12 = sum(Mag_N(index1:index2).^2); %Total energy in the band 1 - normal
    f13 = sum(Mag_N(index3:index4).^2); %Total energy in the band 2 - normal
    f19 = sum(Mag_T(index5:index6).^2); %Total energy in the band 1 - tangential
    f20 = sum(Mag_T(index7:index8).^2); %Total energy in the band 2 - tangential

    x = [feed_rate wheel_speed work_speed f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20];

    y = predict(mdl, x);
end
