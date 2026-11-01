// Minimal offline Squirrel host. No game DLL, executable, renderer or game path.
#include <squirrel.h>
#include <sqstdaux.h>
#include <sqstdio.h>
#include <sqstdmath.h>
#include <sqstdstring.h>
#include <sqstdsystem.h>
#include <chrono>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <random>
#include <string>
#include <algorithm>
#include <queue>
#include <vector>
#include <cmath>
#include <array>
#include <functional>
#include <cstdlib>
#include "sqpcheader.h"
#include "sqvm.h"
#include "sqarray.h"
#include "sqtable.h"

static std::mt19937_64 rng;
static std::uint64_t draws = 0;
static auto began = std::chrono::steady_clock::now();
static std::uint32_t legacy_state = 1;
static std::vector<SQObjectPtr> grid;
static std::vector<std::array<int,6>> neighbors;
static int grid_width=0,grid_height=0;

static void print(HSQUIRRELVM, const SQChar* format, ...) {
    va_list args; va_start(args, format); vfprintf(stdout, format, args); va_end(args);
    fflush(stdout);
}
static void error(HSQUIRRELVM, const SQChar* format, ...) {
    va_list args; va_start(args, format); vfprintf(stderr, format, args); va_end(args);
    fflush(stderr);
}
static SQInteger seed(HSQUIRRELVM v) {
    std::uint64_t value = 0;
    if (sq_gettype(v, 2) == OT_STRING) {
        const SQChar* text; sq_getstring(v, 2, &text);
        for (const unsigned char* p = (const unsigned char*)text; *p; ++p)
            value = value * 65599 + *p;
    } else {
        SQInteger n; if (SQ_FAILED(sq_getinteger(v, 2, &n))) return sq_throwerror(v, "invalid seed");
        value = static_cast<std::uint32_t>(n);
    }
    rng.seed(value); draws = 0; return 0;
}
static SQInteger random_int(HSQUIRRELVM v) {
    SQInteger a, b;
    if (SQ_FAILED(sq_getinteger(v, 2, &a)) || SQ_FAILED(sq_getinteger(v, 3, &b)))
        return sq_throwerror(v, "invalid integer bounds");
    if (b <= a) { sq_pushinteger(v, a); return 1; }
    const std::uint64_t size = std::uint64_t(std::int64_t(b) - a + 1);
    // UINT64_MAX % size + 1 is representable for all signed-32-bit ranges.
    const std::uint64_t remainder = (std::numeric_limits<std::uint64_t>::max() % size + 1) % size;
    std::uint64_t value;
    do { value = rng(); ++draws; }
    while (remainder && value > std::numeric_limits<std::uint64_t>::max() - remainder);
    sq_pushinteger(v, SQInteger(std::int64_t(a) + value % size)); return 1;
}
static SQInteger draw_count(HSQUIRRELVM v) { sq_pushinteger(v, SQInteger(draws)); return 1; }
static SQInteger legacy_rand(HSQUIRRELVM v) {
    legacy_state = legacy_state * 214013U + 2531011U;
    sq_pushinteger(v, SQInteger((legacy_state >> 16) & 32767U)); return 1;
}
static SQInteger integer_field(HSQUIRRELVM v, SQInteger index, const char* key) {
    if(index<0)--index;
    sq_pushstring(v, key, -1); sq_get(v, index); SQInteger result=0;
    sq_getinteger(v, -1, &result); sq_pop(v, 1); return result;
}
static int field(const SQObjectPtr& object,const char* key) {
    SQObjectPtr result;
    return _table(object)->GetStr(key,int(strlen(key)),result)?int(_integer(result)):0;
}
static int tile_id(HSQUIRRELVM v,int index) {
    SQObject object;sq_getstackobj(v,index,&object);return field(SQObjectPtr(object),"ID")-1;
}
static SQInteger bind_tiles(HSQUIRRELVM v) {
    grid.clear();neighbors.clear();SQObject raw;sq_getstackobj(v,2,&raw);SQObjectPtr tiles(raw),column,tile;
    grid_width=int(_array(tiles)->Size());_array(tiles)->Get(0,column);grid_height=int(_array(column)->Size());
    for(int x=0;x<grid_width;x++) {
        _array(tiles)->Get(x,column);
        for(int y=0;y<grid_height;y++) {
            _array(column)->Get(y,tile);grid.push_back(tile);
            std::array<int,6> around;int nx[6]={x,x+1,x+1,x,x-1,x-1};
            int ny[6]={y+1,y+(x&1),y-1+(x&1),y-1,y-1+(x&1),y+(x&1)};
            for(int d=0;d<6;d++)around[d]=nx[d]>=0&&ny[d]>=0&&nx[d]<grid_width&&ny[d]<grid_height?nx[d]*grid_height+ny[d]:-1;
            neighbors.push_back(around);
        }
    }
    return 0;
}
static SQInteger tile_square(HSQUIRRELVM v) {
    SQInteger x,y;sq_getinteger(v,2,&x);sq_getinteger(v,3,&y);
    if(x<0||y<0||x>=grid_width||y>=grid_height)return sq_throwerror(v,"Tile outside world");
    sq_pushobject(v,grid[x*grid_height+y]);return 1;
}
static SQInteger tile_next(HSQUIRRELVM v) {
    SQInteger d;sq_getinteger(v,2,&d);int id=tile_id(v,1);
    if(d<0||d>5||id<0||id>=int(grid.size())||neighbors[id][d]<0)return sq_throwerror(v,"Tile outside world");
    sq_pushobject(v,grid[neighbors[id][d]]);return 1;
}
static SQInteger tile_has_next(HSQUIRRELVM v) {
    SQInteger d;sq_getinteger(v,2,&d);int id=tile_id(v,1);
    sq_pushbool(v,d>=0&&d<6&&id>=0&&id<int(grid.size())&&neighbors[id][d]>=0);return 1;
}
static SQInteger tile_count(HSQUIRRELVM v) {
    SQInteger type;sq_getinteger(v,2,&type);int id=tile_id(v,1),count=0;
    for(int next:neighbors[id])if(next>=0&&field(grid[next],"Type")==type)++count;
    sq_pushinteger(v,count);return 1;
}
static SQInteger tile_count_not(HSQUIRRELVM v) {
    SQInteger type;sq_getinteger(v,2,&type);int id=tile_id(v,1),count=0;
    for(int next:neighbors[id])if(next>=0&&field(grid[next],"Type")!=type)++count;
    sq_pushinteger(v,count);return 1;
}
static int hex_distance(int a,int b) {
    int dq=a/grid_height-b/grid_height,dr=a%grid_height-a/grid_height/2-b%grid_height+b/grid_height/2;
    return std::max(std::abs(dq),std::max(std::abs(dr),std::abs(dq+dr)));
}
static SQInteger tile_distance(HSQUIRRELVM v) {
    sq_pushinteger(v,hex_distance(tile_id(v,1),tile_id(v,2)));return 1;
}
static SQInteger tile_direction(HSQUIRRELVM v) {
    int a=tile_id(v,1),b=tile_id(v,2);
    for(int d=0;d<6;d++)if(neighbors[a][d]==b){sq_pushinteger(v,d);return 1;}
    return sq_throwerror(v,"getDirectionTo requires adjacent tiles");
}
static SQInteger find_region(HSQUIRRELVM v) {
    const int center=tile_id(v,2);SQInteger radius,wanted;sq_getinteger(v,3,&radius);sq_getinteger(v,4,&wanted);
    static std::vector<unsigned int> marks;static unsigned int stamp=0;
    if(marks.size()!=grid.size()){marks.assign(grid.size(),0);stamp=0;}
    if(++stamp==0){std::fill(marks.begin(),marks.end(),0);++stamp;}
    std::vector<int> stack;marks[center]=stamp;int result=0;
    const int order[6]={4,2,5,1,3,0};
    auto append=[&](int id){for(int d:order){int n=neighbors[id][d];if(n>=0&&marks[n]!=stamp)stack.push_back(n);}};
    append(center);
    while(!stack.empty()) {
        int id=stack.back();stack.pop_back();
        if(marks[id]==stamp)continue;
        marks[id]=stamp;
        if(hex_distance(center,id)>radius)continue;
        int region=field(grid[id],"Region");
        // Native callback result 3 prunes this branch. Other pending branches
        // still run and may replace the result; it does not return immediately.
        if(region!=0&&(wanted==0||field(grid[id],"Type")==wanted)){result=region;continue;}
        append(id);
    }
    sq_pushinteger(v,result);return 1;
}
static SQInteger find_type(HSQUIRRELVM v) {
    const int center=tile_id(v,2);SQInteger radius,wanted;sq_getinteger(v,3,&radius);sq_getinteger(v,4,&wanted);
    int found=-1,best=9000;
    auto consider=[&](int id) {
        int distance=hex_distance(center,id);
        if(distance>=best||field(grid[id],"Type")!=wanted)return;
        for(int n:neighbors[id])if(n<0||field(grid[n],"Type")!=wanted)return;
        found=id;best=distance;
    };
    consider(center);
    std::function<void(int,int,int)> visit=[&](int id,int direction,int distance) {
        consider(id);
        if(distance<radius&&neighbors[id][direction]>=0)visit(neighbors[id][direction],direction,distance+1);
        int current=id,side=(direction+1)%6;
        for(int n=distance+1;n<=radius;n++) {
            current=neighbors[current][side];if(current<0)break;consider(current);
        }
    };
    for(int d=0;d<6;d++)if(neighbors[center][d]>=0)visit(neighbors[center][d],d,1);
    if(found<0)sq_pushnull(v);else sq_pushobject(v,grid[found]);return 1;
}
static SQInteger path(HSQUIRRELVM v) {
    // Arguments: column-major tile array, start tile, destination tile, settings.
    const int width=int(sq_getsize(v,2));
    sq_pushinteger(v,0); sq_get(v,2); const int height=int(sq_getsize(v,-1));sq_pop(v,1);
    if(width<=0||height<=0||width>2048||height>2048) return sq_throwerror(v,"Invalid world dimensions");
    const int count=width*height;
    auto coordinates=[&](int index) {
        sq_pushstring(v,"SquareCoords",-1);sq_get(v,index);
        int x=integer_field(v,-1,"X"),y=integer_field(v,-1,"Y");sq_pop(v,1);
        return x*height+y;
    };
    const int start=coordinates(3),end=coordinates(4);
    if(start<0||end<0||start>=count||end>=count) return sq_throwerror(v,"Path endpoint outside world");
    sq_pushstring(v,"ActionPointCosts",-1);sq_get(v,5);
    const int supplied_costs=sq_gettype(v,-1)==OT_ARRAY?int(sq_getsize(v,-1)):0;
    const int cost_count=32;std::vector<float> costs(cost_count,2.0f);
    for(int i=0;i<std::min(supplied_costs,cost_count);i++){sq_pushinteger(v,i);sq_get(v,-2);SQFloat value=0;sq_getfloat(v,-1,&value);costs[i]=value;sq_pop(v,1);}
    sq_pop(v,1);
    sq_pushstring(v,"RoadMult",-1);sq_get(v,5);SQFloat road_mult=1;sq_getfloat(v,-1,&road_mult);sq_pop(v,1);
    sq_pushstring(v,"StopAtRoad",-1);sq_get(v,5);SQBool stop_at_road=SQFalse;sq_getbool(v,-1,&stop_at_road);sq_pop(v,1);
    sq_pushstring(v,"RoadOnly",-1);sq_get(v,5);SQBool road_only=SQFalse;sq_getbool(v,-1,&road_only);sq_pop(v,1);
    const int endq=end/height,endr=end%height-endq/2;
    auto heuristic=[&](int id) {
        int q=id/height,r=id%height-q/2,dq=q-endq,dr=r-endr;
        return 20*std::max(std::abs(dq),std::max(std::abs(dr),std::abs(dq+dr)));
    };
    // Native ordering and integer rounding are part of the map seed contract.
    // Keep a single mutable node per tile and rebuild the heap on decrease-key.
    std::vector<int> priority(count),distance(count),previous(count,-1),parent_direction(count,6),open;
    std::vector<unsigned char> state(count,0);
    auto later=[&](int a,int b){return priority[a]>priority[b];};
    int reached=-1;
    if(start!=end&&field(grid[end],"Type")!=0){open.push_back(start);state[start]=1;}
    while(!open.empty()&&reached<0) {
        std::pop_heap(open.begin(),open.end(),later);int current=open.back();open.pop_back();
        int x=current/height,y=current%height;
        const int nx[6]={x,x+1,x+1,x,x-1,x-1};
        const int ny[6]={y+1,y+(x&1),y-1+(x&1),y-1,y-1+(x&1),y+(x&1)};
        const int directions[6]={0,3,1,5,4,2};
        for(int step=0;step<6;step++) {
            const int d=directions[step];
            if(parent_direction[current]==(d+3)%6)continue;
            if(nx[d]<0||ny[d]<0||nx[d]>=width||ny[d]>=height)continue;
            int next=nx[d]*height+ny[d],type=field(grid[next],"Type"),road=field(grid[next],"RoadDirections");
            if(next==end||(stop_at_road&&road)){previous[next]=current;reached=next;break;}
            if(state[next]==2)continue;
            // Ocean uses +infinity in the original campaign navigation costs.
            // Converting that to int produces a negative cost on Windows.
            if(type<0||type>=cost_count||!std::isfinite(costs[type])||costs[type]<=0){state[next]=2;continue;}
            if(road_only&&!road)continue;
            const int step_cost=int(float(int(costs[type])*10)*(road?road_mult:1.0f));
            const int score=distance[current]+step_cost;
            if(state[next]==0) {
                priority[next]=score+heuristic(next);distance[next]=score;previous[next]=current;parent_direction[next]=d;
                open.push_back(next);std::push_heap(open.begin(),open.end(),later);state[next]=1;
            } else if(score<distance[next]) {
                priority[next]=score+heuristic(next);distance[next]=score;previous[next]=current;parent_direction[next]=d;
                std::make_heap(open.begin(),open.end(),later);
            }
        }
        state[current]=2;
    }
    std::vector<int> result;
    if(reached>=0){for(int i=reached;i!=-1&&i!=start;i=previous[i])result.push_back(i);std::reverse(result.begin(),result.end());}
    sq_newarray(v,0);for(int id:result){sq_pushinteger(v,id);sq_arrayappend(v,-2);}return 1;
}
static SQInteger elapsed(HSQUIRRELVM v) {
    sq_pushfloat(v, SQFloat(std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count())); return 1;
}
static SQInteger trace(HSQUIRRELVM v) {
    static auto last=began;
    if(!std::getenv("BBMOD_WORLDMAP_TRACE"))return 0;
    const SQChar* name;sq_getstring(v,2,&name);auto now=std::chrono::steady_clock::now();
    fprintf(stderr,"%s %.6f\n",name,std::chrono::duration<double>(now-last).count());last=now;return 0;
}
static bool json_string(HSQUIRRELVM v,SQInteger index,std::string& out) {
    const SQChar* value;
    if(SQ_FAILED(sq_getstring(v,index,&value)))return false;
    out+='"';
    const SQInteger size=sq_getsize(v,index);
    for(SQInteger i=0;i<size;i++) {
        const unsigned char c=static_cast<unsigned char>(value[i]);
        if(c=='"'||c=='\\'){out+='\\';out+=char(c);}
        else if(c=='\n')out+="\\n";
        else if(c=='\r')out+="\\r";
        else if(c=='\t')out+="\\t";
        // The existing Squirrel helper indexes signed bytes, so its c>=32
        // condition keeps printable ASCII. Preserve that wire behavior here;
        // Chinese display labels are applied separately by the Python UI.
        else if(c>=32&&c<128)out+=char(c);
    }
    out+='"';return true;
}
static bool json_value(HSQUIRRELVM v,SQInteger index,std::string& out,int depth) {
    if(depth>64)return false;
    if(index<0)index=sq_gettop(v)+index+1;
    const auto type=sq_gettype(v,index);
    char number[64];
    switch(type) {
        case OT_NULL:out+="null";return true;
        case OT_STRING:return json_string(v,index,out);
        case OT_BOOL:{SQBool b;sq_getbool(v,index,&b);out+=b?"true":"false";return true;}
        case OT_INTEGER:{SQInteger n;sq_getinteger(v,index,&n);std::snprintf(number,sizeof(number),"%d",int(n));out+=number;return true;}
        case OT_FLOAT:{
            SQFloat n;sq_getfloat(v,index,&n);
            if(!std::isfinite(n))return false;
            // Squirrel 3.1 tostring() uses %g (six significant digits). Keeping
            // it here preserves the existing JSON values, including scores.
            std::snprintf(number,sizeof(number),"%g",double(n));out+=number;return true;
        }
        case OT_ARRAY:{
            out+='[';const SQInteger size=sq_getsize(v,index);
            for(SQInteger i=0;i<size;i++) {
                if(i)out+=',';
                sq_pushinteger(v,i);
                if(SQ_FAILED(sq_get(v,index))||!json_value(v,-1,out,depth+1))return false;
                sq_pop(v,1);
            }
            out+=']';return true;
        }
        case OT_TABLE:{
            out+='{';bool first=true;sq_pushnull(v);
            while(SQ_SUCCEEDED(sq_next(v,index))) {
                if(!first)out+=',';first=false;
                if(sq_gettype(v,-2)!=OT_STRING||!json_string(v,-2,out))return false;
                out+=':';
                if(!json_value(v,-1,out,depth+1))return false;
                sq_pop(v,2);
            }
            sq_pop(v,1);out+='}';return true;
        }
        default:return false;
    }
}
static SQInteger json_encode(HSQUIRRELVM v) {
    std::string out;out.reserve(1024);
    if(!json_value(v,2,out,0))return sq_throwerror(v,"Unsupported JSON result value");
    sq_pushstring(v,out.data(),SQInteger(out.size()));return 1;
}
static void bind(HSQUIRRELVM v, const char* name, SQFUNCTION function) {
    sq_pushstring(v, name, -1); sq_newclosure(v, function, 0); sq_newslot(v, -3, SQFalse);
}
static void value(HSQUIRRELVM v, const char* name, const char* text) {
    sq_pushstring(v, name, -1); sq_pushstring(v, text, -1); sq_newslot(v, -3, SQFalse);
}
int main(int argc, char** argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: worldmap RULES BOOTSTRAP SEED [STOP_STAGE]\n"); return 2;
    }
    static_assert(sizeof(SQInteger) == 4, "Original rules require signed-32-bit arithmetic");
    static_assert(sizeof(SQFloat) == 4, "Original rules require IEEE single precision");
    auto v = sq_open(2048);
    sq_setprintfunc(v, print, error);
    sqstd_seterrorhandlers(v);
    sq_pushroottable(v);
    sqstd_register_iolib(v); sqstd_register_mathlib(v); sqstd_register_stringlib(v); sqstd_register_systemlib(v);
    bind(v, "_mapSeed", seed); bind(v, "_mapRand", random_int);
    bind(v, "_mapDraws", draw_count); bind(v, "_mapElapsed", elapsed);
    bind(v, "_mapLegacyRand", legacy_rand);bind(v,"_mapPath",path);
    bind(v,"_mapBindTiles",bind_tiles);bind(v,"_mapTileSquare",tile_square);
    bind(v,"_mapTileNext",tile_next);bind(v,"_mapTileHasNext",tile_has_next);
    bind(v,"_mapTileCount",tile_count);bind(v,"_mapTileCountNot",tile_count_not);
    bind(v,"_mapTileDistance",tile_distance);bind(v,"_mapTileDirection",tile_direction);
    bind(v,"_mapFindRegion",find_region);
    bind(v,"_mapFindType",find_type);bind(v,"_mapTrace",trace);
    bind(v,"_mapJSONEncode",json_encode);
    value(v, "WORLD_MAP_RULES", argv[1]); value(v, "WORLD_MAP_SEED", argv[3]);
    std::string script_path(argv[2]);
    const auto separator = script_path.find_last_of("/\\");
    const std::string script_dir = separator == std::string::npos ? "." : script_path.substr(0, separator);
    value(v, "WORLD_MAP_SCRIPT_DIR", script_dir.c_str());
    value(v, "WORLD_MAP_STOP", argc >= 5 ? argv[4] : "complete");
    const bool success = SQ_SUCCEEDED(sqstd_dofile(v, argv[2], SQFalse, SQTrue));
    grid.clear();neighbors.clear();sq_pop(v, 1); sq_close(v); return success ? 0 : 1;
}
