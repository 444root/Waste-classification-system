import { Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { AuthService } from './auth.service';

export interface JwtPayload {
  sub: string;
  ver?: number;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(config: ConfigService, private readonly auth: AuthService) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: config.get<string>(
        'JWT_SECRET',
        'local-development-secret-change-me',
      ),
    });
  }

  async validate(payload: JwtPayload) {
    const user = await this.auth.findPublicUserForSession(
      payload.sub,
      payload.ver ?? 0,
    );
    if (!user) throw new UnauthorizedException('Session is no longer valid');
    return user;
  }
}
