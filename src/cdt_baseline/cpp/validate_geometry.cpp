// Independent combinatorial/causal validator. No simulator object or cache is used.
// A successful check establishes the listed local-manifold properties, not equilibrium.
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using Cell=std::array<int,4>;
using Face=std::array<int,3>;
using Edge=std::array<int,2>;
struct Hash {
    template<std::size_t N> std::size_t operator()(std::array<int,N> const& a) const noexcept {
        std::size_t h=1469598103934665603ULL;
        for(int v:a) {h^=static_cast<std::uint32_t>(v);h*=1099511628211ULL;}
        return h;
    }
};
void require(bool b,const char* message) {if(!b) throw std::runtime_error(message);}
struct UnionFind {
    std::unordered_map<int,int> parent;
    int find(int x) { auto p=parent.find(x); if(p==parent.end()) {parent[x]=x;return x;} if(p->second==x)return x; return parent[x]=find(p->second); }
    void join(int a,int b) {a=find(a);b=find(b);if(a!=b)parent[a]=b;}
    bool connected() {if(parent.empty())return false;int p=find(parent.begin()->first);for(auto const& x:parent)if(find(x.first)!=p)return false;return true;}
};
void circle(std::vector<Edge> const& es) {
    UnionFind u;std::unordered_map<int,int> degree;std::unordered_set<Edge,Hash> seen;
    for(auto e:es) {std::sort(e.begin(),e.end());require(e[0]!=e[1] && seen.insert(e).second,"degenerate/repeated link edge");++degree[e[0]];++degree[e[1]];u.join(e[0],e[1]);}
    for(auto x:degree)require(x.second==2,"link vertex degree != 2");
    require(u.connected(),"link is not one connected circle");
}
struct Occurrence {int tetra;int opposite;int count;};
int run(char const* filename) {
    std::ifstream in(filename);require(bool(in),"cannot open geometry");
    long long ordered,n0,n3,end;in>>ordered>>n0;
    require(bool(in) && ordered==1 && n0>=4 && n0<=100000000,"invalid header/vertex count/ordering");
    std::vector<int> time(n0);int T=0;
    for(auto& t:time){in>>t;require(bool(in)&&t>=0&&t<1000000,"invalid vertex time");T=std::max(T,t+1);}
    require(T>=3,"need >=3 periodic time slices");
    std::vector<bool> used_time(T,false);for(int t:time)used_time[t]=true;
    require(std::all_of(used_time.begin(),used_time.end(),[](bool v){return v;}),"missing time slice");
    in>>end>>n3;require(bool(in)&&end==n0&&n3>=5&&n3<=100000000,"invalid tetrahedron count");
    std::vector<Cell> tetra(n3),neighbors(n3);std::vector<long long> star_count(n0,0),face_count(n0,0),degree(n0,0);
    std::vector<std::vector<int>> stars(n0);std::unordered_set<Cell,Hash> cells;cells.reserve(n3);
    for(int i=0;i<n3;++i){
        for(auto& v:tetra[i]){in>>v;require(bool(in)&&v>=0&&v<n0,"invalid vertex index");stars[v].push_back(i);++star_count[v];}
        for(auto& j:neighbors[i]){in>>j;require(bool(in)&&j>=0&&j<n3&&j!=i,"invalid/self neighbor");}
        auto c=tetra[i];std::sort(c.begin(),c.end());require(std::adjacent_find(c.begin(),c.end())==c.end()&&cells.insert(c).second,"duplicate/degenerate tetrahedron");
        auto nb=neighbors[i];std::sort(nb.begin(),nb.end());require(std::adjacent_find(nb.begin(),nb.end())==nb.end(),"duplicate neighbor");
    }
    in>>end;require(bool(in)&&end==n3,"invalid final sentinel");std::string extra;require(!(in>>extra),"unexpected trailing tokens");
    std::unordered_map<Face,Occurrence,Hash> faces;faces.reserve(2*n3);
    std::unordered_map<Edge,std::vector<Edge>,Hash> links;links.reserve(n3+n0);
    std::vector<std::vector<Face>> slice_faces(T);std::vector<long long> profile(T,0);long long n31=0,n13=0,n22=0;
    for(int i=0;i<n3;++i){
        auto c=tetra[i];std::set<int> ts;for(int v:c)ts.insert(time[v]);require(ts.size()==2,"tetrahedron must span two slices");
        int lower=-1;for(int t:ts)if(ts.count((t+1)%T))lower=t;require(lower>=0,"nonadjacent foliation slices");
        int count=0;for(int v:c)if(time[v]==lower)++count;
        if(count==3){++n31;++profile[lower];}else if(count==1)++n13;else if(count==2)++n22;else throw std::runtime_error("bad tetrahedron type");
        for(int a=0;a<4;++a)for(int b=a+1;b<4;++b){
            Edge edge={c[a],c[b]};std::sort(edge.begin(),edge.end());Edge opposite;int k=0;for(int j=0;j<4;++j)if(j!=a&&j!=b)opposite[k++]=c[j];links[edge].push_back(opposite);
        }
        for(int a=0;a<4;++a){
            Face f;int k=0;for(int j=0;j<4;++j)if(j!=a)f[k++]=c[j];std::sort(f.begin(),f.end());
            int nb=neighbors[i][a];int matches=0;for(int v:f)matches+=std::count(tetra[nb].begin(),tetra[nb].end(),v);
            require(matches==3&&std::count(neighbors[nb].begin(),neighbors[nb].end(),i)==1,"face neighbor mismatch");
            auto pos=faces.find(f);
            if(pos==faces.end()){
                faces.emplace(f,Occurrence{i,a,1});for(int v:f)++face_count[v];
                if(time[f[0]]==time[f[1]]&&time[f[1]]==time[f[2]])slice_faces[time[f[0]]].push_back(f);
            }else{
                require(pos->second.count==1&&pos->second.tetra==nb&&neighbors[nb][pos->second.opposite]==i,"face incidence not exactly two/opposite");
                ++pos->second.count;
            }
        }
    }
    for(auto const& p:faces)require(p.second.count==2,"boundary face");
    for(auto const& p:links){circle(p.second);++degree[p.first[0]];++degree[p.first[1]];}
    std::vector<int> mark(n3,-1);
    for(int v=0;v<n0;++v){
        require(!stars[v].empty(),"unused vertex");require(degree[v]-face_count[v]+star_count[v]==2,"vertex link chi != 2");
        for(int j:stars[v])mark[j]=v;
        std::unordered_set<int> seen;std::vector<int> todo{stars[v][0]};seen.insert(todo[0]);
        while(!todo.empty()){int i=todo.back();todo.pop_back();for(int j:neighbors[i])if(mark[j]==v&&seen.insert(j).second)todo.push_back(j);}
        require(seen.size()==stars[v].size(),"vertex link disconnected");
    }
    for(int t=0;t<T;++t){
        std::unordered_map<Edge,int,Hash> edges;std::unordered_set<int> vertices;std::unordered_map<int,std::vector<Edge>> vl;UnionFind u;
        for(auto f:slice_faces[t]){
            for(int v:f)vertices.insert(v);
            for(int i=0;i<3;++i){Edge e={f[(i+1)%3],f[(i+2)%3]};std::sort(e.begin(),e.end());++edges[e];u.join(e[0],e[1]);vl[f[i]].push_back(e);}
        }
        require(u.connected(),"disconnected/empty spatial slice");for(auto e:edges)require(e.second==2,"spatial edge incidence != 2");
        require(static_cast<long long>(vertices.size())-static_cast<long long>(edges.size())+static_cast<long long>(slice_faces[t].size())==2,"spatial chi != 2");
        for(auto const& x:vl)circle(x.second);
    }
    std::vector<bool> seen(n3,false);seen[0]=true;std::vector<int> todo{0};long long count=0;
    while(!todo.empty()){int i=todo.back();todo.pop_back();++count;for(int j:neighbors[i])if(!seen[j]){seen[j]=true;todo.push_back(j);}}
    require(count==n3,"spacetime disconnected");
    auto n1=static_cast<long long>(links.size()),n2=static_cast<long long>(faces.size());require(n0-n1+n2-n3==0,"spacetime chi != 0");
    std::cout<<"{\"N0\":"<<n0<<",\"N1\":"<<n1<<",\"N2\":"<<n2<<",\"N3\":"<<n3<<",\"N31\":"<<n31<<",\"N13\":"<<n13<<",\"N22\":"<<n22<<",\"time_extent\":"<<T<<",\"chi\":0,\"all_edge_links_circles\":true,\"all_vertex_links_S2\":true,\"all_spatial_slices_S2\":true,\"spatial_volume\":[";
    for(int t=0;t<T;++t){if(t)std::cout<<",";std::cout<<profile[t];}std::cout<<"]}\n";
    return 0;
}
int main(int argc,char** argv){try{require(argc==2,"usage: validate_geometry geometry.dat");return run(argv[1]);}catch(std::exception const& e){std::cerr<<"GEOMETRY_INVALID: "<<e.what()<<"\n";return 2;}}
